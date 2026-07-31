from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import PharmaQSentinelError
from app.models import (
    AuditEvent,
    ComplaintAttachment,
    ComplaintDraft,
    ComplaintMessage,
    EvidenceType,
    FieldEvidence,
    RiskAssessmentVersion,
)
from app.repositories import ComplaintDraftRepository, Pagination
from app.schemas.evidence import (
    EvidenceConflictResponse,
    EvidenceSourceAttachment,
    EvidenceSourceMessage,
    EvidenceStatus,
    FieldEvidenceDetailResponse,
    FieldEvidenceListResponse,
    FieldEvidenceResponse,
    TimelineEntryResponse,
    TimelineListResponse,
)

CRITICAL_CONFLICT_FIELDS = {
    "batch_lot_number",
    "product_strength_grade",
    "product_name",
    "adverse_event_signal",
    "quantity_affected",
}


def canonical_json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): canonical_json_value(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [canonical_json_value(item) for item in value]
    return value


def _display_value(value: dict[str, Any] | None) -> Any:
    if not isinstance(value, dict):
        return value
    return canonical_json_value(value.get("value"))


def _provider_from_value(value: dict[str, Any] | None, key: str) -> str | None:
    if not isinstance(value, dict):
        return None
    provider = value.get(key)
    return str(provider) if provider not in (None, "") else None


def _normalised(value: dict[str, Any] | None) -> bool:
    if not isinstance(value, dict):
        return False
    if "normalised" not in value:
        return False
    return canonical_json_value(value.get("normalised")) != canonical_json_value(value.get("raw", value.get("value")))


def _status_for_evidence(evidence: FieldEvidence, *, field_has_conflict: bool, active_value: Any) -> EvidenceStatus:
    value = _display_value(evidence.field_value)
    if not evidence.is_active:
        return EvidenceStatus.SUPERSEDED
    if field_has_conflict and canonical_json_value(value) != canonical_json_value(active_value):
        return EvidenceStatus.CONFLICTING_SOURCE
    if evidence.evidence_type == EvidenceType.USER_CORRECTION.value:
        return EvidenceStatus.USER_CORRECTION
    if evidence.evidence_type == EvidenceType.AI_INFERENCE.value:
        return EvidenceStatus.AI_INFERENCE
    if evidence.evidence_type == EvidenceType.SYSTEM_RECORD.value:
        return EvidenceStatus.SYSTEM_REFERENCE
    if _normalised(evidence.field_value):
        return EvidenceStatus.NORMALISED_SOURCE
    return EvidenceStatus.EXPLICIT_SOURCE


def _active_reason(evidence: FieldEvidence | None) -> str:
    if evidence is None:
        return "No active evidence is available."
    if evidence.evidence_type == EvidenceType.USER_CORRECTION.value:
        return "user correction"
    if evidence.confidence is not None:
        return "higher-confidence explicit evidence"
    return "currently active source evidence"


def _field_conflicts(evidence_rows: list[FieldEvidence]) -> list[EvidenceConflictResponse]:
    conflicts: list[EvidenceConflictResponse] = []
    by_field: dict[str, list[FieldEvidence]] = {}
    for evidence in evidence_rows:
        by_field.setdefault(evidence.field_name, []).append(evidence)

    for field_name, rows in by_field.items():
        values = {str(canonical_json_value(_display_value(row.field_value))) for row in rows}
        if len(values) <= 1:
            continue
        active = next((row for row in rows if row.is_active), None)
        current_value = _display_value(active.field_value) if active else None
        conflicting_ids = [row.id for row in rows if row is not active]
        is_critical = field_name in CRITICAL_CONFLICT_FIELDS
        conflicts.append(
            EvidenceConflictResponse(
                field_name=field_name,
                is_critical=is_critical,
                current_value=current_value,
                active_evidence_id=active.id if active else None,
                conflicting_evidence_ids=conflicting_ids,
                active_reason=_active_reason(active),
                description=(
                    f"{field_name} has conflicting preserved source values. "
                    f"The active value is retained because of {_active_reason(active)}."
                ),
            )
        )
    return conflicts


def _source_message(message: ComplaintMessage | None) -> EvidenceSourceMessage | None:
    if message is None:
        return None
    return EvidenceSourceMessage(
        id=message.id,
        role=message.role,
        message_text=message.message_text,
        created_at=message.created_at,
    )


def _source_attachment(attachment: ComplaintAttachment | None) -> EvidenceSourceAttachment | None:
    if attachment is None:
        return None
    return EvidenceSourceAttachment(
        id=attachment.id,
        original_filename=attachment.original_filename,
        mime_type=attachment.mime_type,
        file_size=attachment.file_size,
        sha256_checksum=attachment.sha256_checksum,
        extraction_status=attachment.extraction_status,
        created_at=attachment.created_at,
        uploaded_by=attachment.uploaded_by,
    )


def _evidence_response(
    evidence: FieldEvidence,
    *,
    conflicts: list[EvidenceConflictResponse],
) -> FieldEvidenceResponse:
    conflict = next((item for item in conflicts if item.field_name == evidence.field_name), None)
    active_value = conflict.current_value if conflict else _display_value(evidence.field_value)
    status = _status_for_evidence(evidence, field_has_conflict=conflict is not None, active_value=active_value)
    return FieldEvidenceResponse(
        id=evidence.id,
        draft_id=evidence.draft_id,
        field_name=evidence.field_name,
        field_value=canonical_json_value(evidence.field_value),
        display_value=_display_value(evidence.field_value),
        evidence_type=evidence.evidence_type,
        evidence_status=status,
        conflict_status="CONFLICT" if conflict else "NONE",
        active_reason=_active_reason(evidence) if evidence.is_active else None,
        source_message_id=evidence.source_message_id,
        source_attachment_id=evidence.source_attachment_id,
        source_message=_source_message(evidence.source_message),
        source_attachment=_source_attachment(evidence.source_attachment),
        page_number=evidence.page_number,
        paragraph_index=evidence.paragraph_index,
        source_excerpt=evidence.source_excerpt,
        confidence=evidence.confidence,
        extraction_method=evidence.extraction_method,
        is_explicit=evidence.is_explicit,
        is_normalised=_normalised(evidence.field_value),
        is_inferred=evidence.evidence_type == EvidenceType.AI_INFERENCE.value or not evidence.is_explicit,
        is_active=evidence.is_active,
        provider_name=_provider_from_value(evidence.field_value, "provider"),
        actual_model=_provider_from_value(evidence.field_value, "actual_model"),
        created_at=evidence.created_at,
    )


def _all_evidence_statement(draft_id: str):
    return (
        select(FieldEvidence)
        .where(FieldEvidence.draft_id == draft_id)
        .options(selectinload(FieldEvidence.source_message), selectinload(FieldEvidence.source_attachment))
        .order_by(FieldEvidence.created_at.asc(), FieldEvidence.id.asc())
    )


def _filtered_evidence_statement(
    draft_id: str,
    *,
    field_name: str | None,
    active_only: bool,
    evidence_type: str | None,
    attachment_id: str | None,
):
    statement = _all_evidence_statement(draft_id)
    if field_name:
        statement = statement.where(FieldEvidence.field_name == field_name)
    if active_only:
        statement = statement.where(FieldEvidence.is_active.is_(True))
    if evidence_type:
        statement = statement.where(FieldEvidence.evidence_type == evidence_type)
    if attachment_id:
        statement = statement.where(FieldEvidence.source_attachment_id == attachment_id)
    return statement


def list_evidence(
    db: Session,
    *,
    draft_id: str,
    field_name: str | None = None,
    active_only: bool = False,
    evidence_type: str | None = None,
    attachment_id: str | None = None,
    pagination: Pagination | None = None,
) -> FieldEvidenceListResponse:
    ComplaintDraftRepository(db).get_required(draft_id)
    all_rows = list(db.scalars(_all_evidence_statement(draft_id)).all())
    conflicts = _field_conflicts(all_rows)
    statement = _filtered_evidence_statement(
        draft_id,
        field_name=field_name,
        active_only=active_only,
        evidence_type=evidence_type,
        attachment_id=attachment_id,
    )
    if pagination:
        statement = statement.limit(pagination.limit).offset(pagination.offset)
    rows = list(db.scalars(statement).all())
    limit = pagination.limit if pagination else len(rows)
    offset = pagination.offset if pagination else 0
    return FieldEvidenceListResponse(
        items=[_evidence_response(row, conflicts=conflicts) for row in rows],
        limit=limit,
        offset=offset,
        next_offset=offset + limit if pagination and len(rows) == limit else None,
        conflicts=conflicts,
        critical_conflicts_block_save=any(conflict.is_critical for conflict in conflicts),
    )


def get_field_evidence_detail(db: Session, *, draft_id: str, field_name: str) -> FieldEvidenceDetailResponse:
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    all_rows = list(db.scalars(_all_evidence_statement(draft_id)).all())
    rows = [row for row in all_rows if row.field_name == field_name]
    if not rows:
        raise PharmaQSentinelError(f"No evidence found for field: {field_name}", status_code=404)
    conflicts = [item for item in _field_conflicts(all_rows) if item.field_name == field_name]
    responses = [_evidence_response(row, conflicts=conflicts) for row in rows]
    active = next((item for item in responses if item.is_active), None)
    return FieldEvidenceDetailResponse(
        field_name=field_name,
        current_value=canonical_json_value(getattr(draft, field_name, None)),
        current_active_evidence=active,
        evidence_history=responses,
        conflicts=conflicts,
        critical_conflict_unresolved=any(conflict.is_critical for conflict in conflicts),
    )


def _audit_title(event: AuditEvent) -> tuple[str, str]:
    if event.event_type == "DRAFT_CREATED":
        return "Draft created", "An empty complaint draft was created."
    if event.event_type == "DOCUMENT_UPLOADED":
        return "Attachment uploaded", "A source document was preserved for this draft."
    if event.event_type == "DOCUMENT_TEXT_EXTRACTED":
        return "Document text extracted", "Derived document text was extracted from the preserved upload."
    if event.field_name and event.old_value and event.new_value:
        old_value = event.old_value.get("value")
        new_value = event.new_value.get("value")
        if old_value in (None, "") and new_value not in (None, ""):
            return "Field populated", f"{event.field_name} was populated from source evidence."
        if new_value in (None, ""):
            return "Field cleared", f"{event.field_name} was cleared through an audited operation."
        return "Field corrected", f"{event.field_name} changed from {old_value} to {new_value}."
    return event.event_type.replace("_", " ").title(), event.reason or "Audited draft activity."


def _timeline_from_audit(event: AuditEvent) -> TimelineEntryResponse:
    title, description = _audit_title(event)
    metadata = event.metadata_json or {}
    evidence_refs = metadata.get("evidence_ids") if isinstance(metadata.get("evidence_ids"), list) else []
    attachment_refs = []
    if metadata.get("source_attachment_id"):
        attachment_refs.append(str(metadata["source_attachment_id"]))
    if event.new_value and event.new_value.get("attachment_id"):
        attachment_refs.append(str(event.new_value["attachment_id"]))
    return TimelineEntryResponse(
        event_id=event.id,
        event_type=event.event_type,
        actor=event.actor_type,
        timestamp=event.created_at,
        title=title,
        description=description,
        affected_fields=[event.field_name] if event.field_name else [],
        old_value=canonical_json_value(event.old_value),
        new_value=canonical_json_value(event.new_value),
        evidence_references=[str(item) for item in evidence_refs],
        attachment_references=attachment_refs,
        provider_name=event.provider_name,
        actual_model=event.actual_model,
    )


def _timeline_from_message(message: ComplaintMessage) -> TimelineEntryResponse:
    title = "User message" if message.role == "USER" else "Assistant response"
    return TimelineEntryResponse(
        event_id=message.id,
        event_type=title.upper().replace(" ", "_"),
        actor=message.role,
        timestamp=message.created_at,
        title=title,
        description=message.message_text[:240],
        attachment_references=[message.attachment_id] if message.attachment_id else [],
    )


def _timeline_from_attachment(attachment: ComplaintAttachment) -> TimelineEntryResponse:
    return TimelineEntryResponse(
        event_id=attachment.id,
        event_type="ATTACHMENT_UPLOAD",
        actor=attachment.uploaded_by or "USER",
        timestamp=attachment.created_at,
        title="Attachment upload",
        description=f"{attachment.original_filename} was uploaded as preserved source material.",
        attachment_references=[attachment.id],
    )


def _timeline_from_risk(version: RiskAssessmentVersion) -> TimelineEntryResponse:
    metadata = version.supporting_evidence or {}
    evidence_refs = metadata.get("evidence_ids") if isinstance(metadata.get("evidence_ids"), list) else []
    route = version.safety_route or "UNDETERMINED"
    return TimelineEntryResponse(
        event_id=version.id,
        event_type="RISK_ASSESSMENT_VERSION",
        actor="AI_AGENT",
        timestamp=version.created_at,
        title="Risk assessment version",
        description=f"Draft severity {version.severity}, priority {version.priority}, route {route}; requires authorised QA review.",
        affected_fields=["suggested_severity", "suggested_priority", "safety_route"],
        new_value={
            "severity": version.severity,
            "priority": version.priority,
            "safety_route": route,
        },
        evidence_references=[str(item) for item in evidence_refs],
        provider_name=version.provider_name,
        actual_model=version.actual_model,
    )


def list_timeline(
    db: Session,
    *,
    draft_id: str,
    actor: str | None = None,
    event_type: str | None = None,
    field_name: str | None = None,
    pagination: Pagination | None = None,
) -> TimelineListResponse:
    draft: ComplaintDraft = ComplaintDraftRepository(db).get_required(draft_id)
    entries: list[TimelineEntryResponse] = [
        TimelineEntryResponse(
            event_id=f"draft-created-{draft.id}",
            event_type="DRAFT_CREATED",
            actor="SYSTEM" if not draft.created_by else "USER",
            timestamp=draft.created_at,
            title="Draft created",
            description="Complaint draft database record was created.",
            affected_fields=[],
        )
    ]
    entries.extend(_timeline_from_audit(event) for event in db.scalars(select(AuditEvent).where(AuditEvent.draft_id == draft_id)).all())
    entries.extend(_timeline_from_message(message) for message in db.scalars(select(ComplaintMessage).where(ComplaintMessage.draft_id == draft_id)).all())
    entries.extend(_timeline_from_attachment(item) for item in db.scalars(select(ComplaintAttachment).where(ComplaintAttachment.draft_id == draft_id)).all())
    entries.extend(_timeline_from_risk(item) for item in db.scalars(select(RiskAssessmentVersion).where(RiskAssessmentVersion.draft_id == draft_id)).all())

    conflicts = _field_conflicts(list(db.scalars(_all_evidence_statement(draft_id)).all()))
    for conflict in conflicts:
        entries.append(
            TimelineEntryResponse(
                event_id=f"conflict-{conflict.field_name}-{conflict.active_evidence_id or 'none'}",
                event_type="CONFLICT_DETECTED",
                actor="SYSTEM",
                timestamp=draft.updated_at,
                title="Conflict detected",
                description=conflict.description,
                affected_fields=[conflict.field_name],
                evidence_references=[ref for ref in [conflict.active_evidence_id, *conflict.conflicting_evidence_ids] if ref],
            )
        )

    entries.sort(key=lambda item: (canonical_json_value(item.timestamp), item.event_id))
    if actor:
        entries = [item for item in entries if item.actor == actor]
    if event_type:
        entries = [item for item in entries if item.event_type == event_type]
    if field_name:
        entries = [item for item in entries if field_name in item.affected_fields]

    limit = pagination.limit if pagination else len(entries)
    offset = pagination.offset if pagination else 0
    paged = entries[offset: offset + limit]
    return TimelineListResponse(
        items=paged,
        limit=limit,
        offset=offset,
        next_offset=offset + limit if len(paged) == limit and offset + limit < len(entries) else None,
    )
