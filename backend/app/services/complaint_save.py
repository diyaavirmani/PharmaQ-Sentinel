from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.exceptions import PharmaQSentinelError
from app.models import (
    ActorType,
    AuditEvent,
    Complaint,
    ComplaintAttachment,
    ComplaintDraft,
    ComplaintStatus,
    ExtractionStatus,
    FieldEvidence,
    RiskAssessmentVersion,
)
from app.models.base import utc_now
from app.repositories.audit_events import AuditEventRepository
from app.repositories.complaint_versions import ComplaintVersionRepository
from app.repositories.complaints import ComplaintRepository
from app.repositories.risk_assessments import RiskAssessmentVersionRepository
from app.schemas.complaints import SaveComplaintRequest
from app.services.complaint_drafts import MUTABLE_COMPLAINT_FIELDS
from app.services.complaint_snapshots import checksum_snapshot
from app.services.evidence_lock import canonical_json_value, list_evidence


class ComplaintSaveConflictError(PharmaQSentinelError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409)


class ComplaintSaveValidationError(PharmaQSentinelError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


def _meaningful_text(value: str | None, *, minimum: int = 10) -> bool:
    return value is not None and len(value.strip()) >= minimum


def _missing_information(draft: ComplaintDraft) -> dict[str, Any] | None:
    if not draft.missing_fields:
        return None
    return canonical_json_value(draft.missing_fields)


def _is_extraction_active(db: Session, draft_id: str) -> bool:
    active_statuses = {
        ExtractionStatus.PENDING.value,
        ExtractionStatus.VALIDATING.value,
        ExtractionStatus.EXTRACTING.value,
    }
    statement = select(ComplaintAttachment).where(
        ComplaintAttachment.draft_id == draft_id,
        ComplaintAttachment.extraction_status.in_(active_statuses),
    )
    return db.scalars(statement).first() is not None


def _critical_safety_signal_present(draft: ComplaintDraft) -> bool:
    return any(
        [
            draft.adverse_event_signal is True,
            draft.counterfeit_signal is True,
            draft.suggested_severity == "CRITICAL",
            draft.safety_route
            in {
                "POSSIBLE_ADVERSE_EVENT",
                "QUALITY_AND_ADVERSE_EVENT",
                "COUNTERFEIT_OR_TAMPERING",
            },
        ]
    )


def _copy_official_fields(draft: ComplaintDraft) -> dict[str, Any]:
    return {field_name: getattr(draft, field_name) for field_name in MUTABLE_COMPLAINT_FIELDS}


def _active_evidence_references(db: Session, draft_id: str) -> list[dict[str, Any]]:
    statement = (
        select(FieldEvidence)
        .where(FieldEvidence.draft_id == draft_id, FieldEvidence.is_active.is_(True))
        .order_by(FieldEvidence.field_name.asc(), FieldEvidence.created_at.asc())
    )
    return [
        {
            "id": item.id,
            "field_name": item.field_name,
            "evidence_type": item.evidence_type,
            "source_attachment_id": item.source_attachment_id,
            "source_message_id": item.source_message_id,
            "confidence": canonical_json_value(item.confidence),
            "created_at": canonical_json_value(item.created_at),
        }
        for item in db.scalars(statement).all()
    ]


def _source_attachment_references(db: Session, draft_id: str) -> list[dict[str, Any]]:
    statement = (
        select(ComplaintAttachment)
        .where(ComplaintAttachment.draft_id == draft_id)
        .order_by(ComplaintAttachment.created_at.asc(), ComplaintAttachment.id.asc())
    )
    return [
        {
            "id": item.id,
            "original_filename": item.original_filename,
            "mime_type": item.mime_type,
            "file_size": item.file_size,
            "sha256_checksum": item.sha256_checksum,
            "extraction_status": item.extraction_status,
            "created_at": canonical_json_value(item.created_at),
        }
        for item in db.scalars(statement).all()
    ]


def _risk_reference(risk: RiskAssessmentVersion) -> dict[str, Any]:
    return {
        "id": risk.id,
        "version_number": risk.version_number,
        "severity": risk.severity,
        "priority": risk.priority,
        "safety_route": risk.safety_route,
        "confidence": canonical_json_value(risk.confidence),
        "provider_name": risk.provider_name,
        "actual_model": risk.actual_model,
        "created_at": canonical_json_value(risk.created_at),
    }


def _saved_snapshot(
    db: Session,
    *,
    draft: ComplaintDraft,
    complaint: Complaint,
    risk: RiskAssessmentVersion,
    request: SaveComplaintRequest,
    saved_at: Any,
) -> dict[str, Any]:
    official_fields = {
        field_name: canonical_json_value(getattr(complaint, field_name))
        for field_name in MUTABLE_COMPLAINT_FIELDS
    }
    snapshot = {
        "complaint": {
            "id": complaint.id,
            "complaint_number": complaint.complaint_number,
            "status": complaint.status,
            "committed_from_draft_id": draft.id,
            "committed_at": canonical_json_value(saved_at),
            "committed_by": complaint.committed_by,
            "review_meaning": request.review_meaning,
            "missing_information_acknowledged": request.missing_information_acknowledged,
            "change_reason": request.change_reason,
            "official_fields": official_fields,
        },
        "missing_information": _missing_information(draft),
        "active_evidence_references": _active_evidence_references(db, draft.id),
        "risk_assessment_reference": _risk_reference(risk),
        "safety_route": complaint.safety_route,
        "source_attachment_references": _source_attachment_references(db, draft.id),
        "saved_timestamp": canonical_json_value(saved_at),
    }
    return canonical_json_value(snapshot)


def _reserve_complaint_number(db: Session, *, today: date) -> str:
    year = today.year
    now = utc_now()
    # MySQL LAST_INSERT_ID gives an atomic per-connection reservation without counting complaints.
    db.execute(
        text(
            """
            INSERT INTO complaint_number_sequences (`year`, next_number, updated_at)
            VALUES (:year, LAST_INSERT_ID(2), :updated_at)
            ON DUPLICATE KEY UPDATE
              next_number = LAST_INSERT_ID(next_number + 1),
              updated_at = :updated_at
            """
        ),
        {"year": year, "updated_at": now},
    )
    reserved_next_number = db.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
    sequence_number = int(reserved_next_number) - 1
    return f"PQC-{year}-{sequence_number:06d}"


def _locked_draft(db: Session, draft_id: str) -> ComplaintDraft | None:
    statement = select(ComplaintDraft).where(ComplaintDraft.id == draft_id).with_for_update()
    return db.scalars(statement).first()


def _validate_save(
    db: Session,
    *,
    draft: ComplaintDraft,
    request: SaveComplaintRequest,
    risk: RiskAssessmentVersion | None,
) -> None:
    if not _meaningful_text(draft.detailed_description):
        raise ComplaintSaveValidationError("A meaningful complaint description is required before saving.")
    if not _meaningful_text(draft.product_name, minimum=2) and not _meaningful_text(
        draft.batch_lot_number,
        minimum=2,
    ):
        raise ComplaintSaveValidationError("Product identification is required before saving.")
    if not _meaningful_text(request.reviewed_by, minimum=1):
        raise ComplaintSaveValidationError("Reviewer is required before saving.")
    if _is_extraction_active(db, draft.id):
        raise ComplaintSaveConflictError("Complaint extraction is still processing.")
    if risk is None:
        raise ComplaintSaveConflictError("A draft risk assessment must exist before saving.")
    evidence_result = list_evidence(db, draft_id=draft.id)
    if evidence_result.critical_conflicts_block_save:
        raise ComplaintSaveConflictError("Unresolved critical evidence conflict blocks saving.")
    missing_info = _missing_information(draft)
    if missing_info and not request.missing_information_acknowledged:
        raise ComplaintSaveConflictError("Acknowledge non-critical missing information before saving.")
    if _critical_safety_signal_present(draft) and "review" not in request.review_meaning.lower():
        raise ComplaintSaveConflictError("Critical safety signal must be acknowledged for review before saving.")


def save_complaint(db: Session, *, draft_id: str, request: SaveComplaintRequest) -> Complaint:
    complaints = ComplaintRepository(db)
    existing_by_key = complaints.get_by_save_idempotency_key(request.idempotency_key)
    if existing_by_key is not None:
        if existing_by_key.committed_from_draft_id == draft_id:
            return existing_by_key
        raise ComplaintSaveConflictError("Idempotency key was already used for a different complaint.")

    draft = _locked_draft(db, draft_id)
    if draft is None:
        raise PharmaQSentinelError(f"ComplaintDraft not found: {draft_id}", status_code=404)

    existing_for_draft = complaints.get_by_committed_from_draft_id(draft.id)
    if existing_for_draft is not None:
        if existing_for_draft.save_idempotency_key == request.idempotency_key:
            return existing_for_draft
        raise ComplaintSaveConflictError("Complaint draft has already been saved.")
    if draft.status in {
        ComplaintStatus.COMMITTED.value,
        ComplaintStatus.CLOSED.value,
        ComplaintStatus.CANCELLED.value,
    }:
        raise ComplaintSaveConflictError("Complaint draft is locked by a completed save operation.")

    risk = RiskAssessmentVersionRepository(db).get_latest_for_draft(draft.id)
    _validate_save(db, draft=draft, request=request, risk=risk)
    assert risk is not None

    saved_at = utc_now()
    complaint = complaints.create(
        complaint_number=_reserve_complaint_number(db, today=saved_at.date()),
        committed_by=request.reviewed_by,
        committed_at=saved_at,
        current_version_number=1,
        status=ComplaintStatus.COMMITTED.value,
        committed_from_draft_id=draft.id,
        save_idempotency_key=request.idempotency_key,
        review_meaning=request.review_meaning,
        missing_information_acknowledged=request.missing_information_acknowledged,
        unresolved_missing_information=_missing_information(draft),
        latest_risk_assessment_id=risk.id,
        **_copy_official_fields(draft),
    )
    snapshot = _saved_snapshot(db, draft=draft, complaint=complaint, risk=risk, request=request, saved_at=saved_at)
    checksum = checksum_snapshot(snapshot)
    ComplaintVersionRepository(db).append(
        complaint_id=complaint.id,
        version_number=1,
        snapshot=snapshot,
        checksum=checksum,
        created_by=request.reviewed_by,
        created_at=saved_at,
        change_reason=request.change_reason,
    )
    AuditEventRepository(db).append(
        draft_id=draft.id,
        complaint_id=complaint.id,
        event_type="SAVE_COMPLAINT",
        actor_type=ActorType.USER,
        actor_identifier=request.reviewed_by,
        tool_name="save_complaint",
        old_value={"status": draft.status},
        new_value={
            "status": ComplaintStatus.COMMITTED.value,
            "complaint_id": complaint.id,
            "complaint_number": complaint.complaint_number,
        },
        reason=request.change_reason,
        metadata_json={
            "idempotency_key": request.idempotency_key,
            "review_meaning": request.review_meaning,
            "missing_information_acknowledged": request.missing_information_acknowledged,
            "missing_information": _missing_information(draft),
            "version_checksum": checksum,
            "risk_assessment_id": risk.id,
        },
    )
    draft.status = ComplaintStatus.COMMITTED.value
    draft.updated_at = saved_at
    db.flush()
    return complaint


def complaint_timeline(db: Session, *, complaint_id: str) -> list[dict[str, Any]]:
    complaint = ComplaintRepository(db).get_required(complaint_id)
    entries: list[dict[str, Any]] = [
        {
            "event_id": f"complaint-saved-{complaint.id}",
            "event_type": "SAVE_COMPLAINT",
            "actor": complaint.committed_by,
            "timestamp": complaint.committed_at,
            "title": "Complaint saved",
            "description": f"{complaint.complaint_number} was saved to the demonstration QMS ledger.",
            "affected_fields": [],
            "old_value": None,
            "new_value": {"status": complaint.status},
            "evidence_references": [],
            "attachment_references": [],
            "provider_name": None,
            "actual_model": None,
        }
    ]
    audit_statement = select(AuditEvent).where(AuditEvent.complaint_id == complaint_id)
    for event in db.scalars(audit_statement).all():
        entries.append(
            {
                "event_id": event.id,
                "event_type": event.event_type,
                "actor": event.actor_type,
                "timestamp": event.created_at,
                "title": event.event_type.replace("_", " ").title(),
                "description": event.reason or "Audited complaint ledger activity.",
                "affected_fields": [event.field_name] if event.field_name else [],
                "old_value": canonical_json_value(event.old_value),
                "new_value": canonical_json_value(event.new_value),
                "evidence_references": [],
                "attachment_references": [],
                "provider_name": event.provider_name,
                "actual_model": event.actual_model,
            }
        )
    entries.sort(key=lambda item: (canonical_json_value(item["timestamp"]), str(item["event_id"])))
    return entries
