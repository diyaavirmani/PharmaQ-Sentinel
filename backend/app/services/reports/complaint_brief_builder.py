from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import PharmaQSentinelError
from app.models import (
    AuditEvent,
    BatchImpactRun,
    Complaint,
    ComplaintAttachment,
    DuplicateAnalysisRun,
    FieldEvidence,
    InvestigationPlaybookRun,
    QualityWarRoomRun,
    RiskAssessmentVersion,
)
from app.models.base import utc_now
from app.repositories import ComplaintRepository, ComplaintVersionRepository
from app.services.complaint_save import complaint_timeline
from app.services.reports.checksum import sha256_hexdigest
from app.services.reports.complaint_brief_schema import (
    INSPECTION_BRIEF_DISCLAIMER,
    BriefField,
    ComplaintBrief,
    EvidenceReference,
    ReportSection,
    SourceDocumentReference,
)

IMPORTANT_FIELDS = [
    ("complaint_source", "Complaint Source"),
    ("customer_name", "Customer Name"),
    ("customer_contact", "Customer Contact"),
    ("country_market", "Country/Market"),
    ("product_type", "Product Type"),
    ("product_name", "Product Name"),
    ("product_strength_grade", "Product Strength/Grade"),
    ("dosage_form", "Dosage Form"),
    ("batch_lot_number", "Batch/Lot Number"),
    ("manufacturing_date", "Manufacturing Date"),
    ("expiry_retest_date", "Expiry/Retest Date"),
    ("quantity_affected", "Quantity Affected"),
    ("quantity_unit", "Quantity Unit"),
    ("complaint_type", "Complaint Type"),
    ("complaint_date", "Complaint Date"),
    ("detailed_description", "Detailed Complaint Description"),
    ("sample_available", "Sample Available"),
    ("patient_consumed_product", "Patient Consumed Product"),
    ("adverse_event_signal", "Adverse Event Signal"),
    ("counterfeit_signal", "Counterfeit Signal"),
    ("storage_conditions", "Storage Conditions"),
    ("suggested_severity", "Suggested Severity"),
    ("suggested_priority", "Suggested Priority"),
    ("safety_route", "Safety Route"),
    ("risk_rationale", "Risk Rationale"),
    ("potential_hazard", "Potential Hazard"),
    ("suggested_next_action", "Suggested Next Action"),
    ("risk_confidence", "Risk Confidence"),
]


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _display(value: Any) -> str:
    if value is None or value == "":
        return "Not provided"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return str(_json_value(value))
    return str(_json_value(value))


def _latest_for_draft(db: Session, model: Any, draft_id: str, order_column: Any) -> Any | None:
    statement = select(model).where(model.draft_id == draft_id).order_by(order_column.desc())
    return db.scalars(statement).first()


def _source_documents(db: Session, draft_id: str | None, snapshot: dict[str, Any]) -> list[SourceDocumentReference]:
    snapshot_refs = snapshot.get("source_attachment_references") or []
    if snapshot_refs:
        return [
            SourceDocumentReference(
                original_filename=item.get("original_filename") or "Unknown source",
                mime_type=item.get("mime_type") or "application/octet-stream",
                checksum=item.get("sha256_checksum") or "Not provided",
                upload_date=item.get("created_at"),
            )
            for item in snapshot_refs
        ]
    if not draft_id:
        return []
    statement = select(ComplaintAttachment).where(ComplaintAttachment.draft_id == draft_id)
    return [
        SourceDocumentReference(
            original_filename=item.original_filename,
            mime_type=item.mime_type,
            checksum=item.sha256_checksum,
            upload_date=_json_value(item.created_at),
        )
        for item in db.scalars(statement).all()
    ]


def _evidence_rows(db: Session, draft_id: str | None, official_fields: dict[str, Any]) -> list[EvidenceReference]:
    if not draft_id:
        return []
    statement = select(FieldEvidence).where(FieldEvidence.draft_id == draft_id).order_by(
        FieldEvidence.field_name.asc(),
        FieldEvidence.created_at.asc(),
    )
    rows: list[EvidenceReference] = []
    for item in db.scalars(statement).all():
        rows.append(
            EvidenceReference(
                field_name=item.field_name,
                current_value=official_fields.get(item.field_name),
                source_type=item.evidence_type,
                source_excerpt=item.source_excerpt,
                page_number=item.page_number,
                confidence=_json_value(item.confidence),
                user_corrected=item.evidence_type == "USER_CORRECTION",
                created_at=_json_value(item.created_at),
            )
        )
    return rows


def _audit_rows(db: Session, complaint: Complaint) -> list[dict[str, Any]]:
    return [_json_value(item) for item in complaint_timeline(db, complaint_id=complaint.id)]


def _user_corrections(db: Session, draft_id: str | None, complaint_id: str) -> list[dict[str, Any]]:
    statement = select(AuditEvent).where(AuditEvent.complaint_id == complaint_id)
    if draft_id:
        statement = statement.union_all(select(AuditEvent).where(AuditEvent.draft_id == draft_id))
    rows = []
    for event in db.scalars(select(AuditEvent).where((AuditEvent.complaint_id == complaint_id) | (AuditEvent.draft_id == draft_id))).all():
        if event.field_name or "PATCH" in event.event_type or "CORRECTION" in event.event_type:
            rows.append(
                {
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "field_name": event.field_name,
                    "old_value": _json_value(event.old_value),
                    "new_value": _json_value(event.new_value),
                    "actor": event.actor_identifier or event.actor_type,
                    "created_at": _json_value(event.created_at),
                    "reason": event.reason,
                }
            )
    return rows


def _risk_rows(db: Session, draft_id: str | None, complaint: Complaint, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    risk_ref = snapshot.get("risk_assessment_reference")
    if risk_ref:
        rows.append({"scope": "snapshot_reference", **risk_ref})
    if draft_id:
        latest = _latest_for_draft(db, RiskAssessmentVersion, draft_id, RiskAssessmentVersion.version_number)
        if latest:
            rows.append(
                {
                    "scope": "latest",
                    "id": latest.id,
                    "severity": latest.severity,
                    "priority": latest.priority,
                    "safety_route": latest.safety_route,
                    "rationale": latest.risk_rationale,
                    "confidence": _json_value(latest.confidence),
                    "provider_name": latest.provider_name,
                    "requested_model": latest.requested_model,
                    "actual_model": latest.actual_model,
                    "created_at": _json_value(latest.created_at),
                }
            )
    if not rows:
        rows.append(
            {
                "scope": "committed_fields",
                "severity": complaint.suggested_severity,
                "priority": complaint.suggested_priority,
                "safety_route": complaint.safety_route,
            }
        )
    return rows


def _provider_rows(
    *,
    risk_rows: list[dict[str, Any]],
    batch_run: BatchImpactRun | None,
    war_room_run: QualityWarRoomRun | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for risk in risk_rows:
        if risk.get("provider_name") or risk.get("actual_model"):
            rows.append(
                {
                    "tool": "Risk Assessment",
                    "provider": risk.get("provider_name"),
                    "model": risk.get("actual_model"),
                    "prompt_version": "pharma-risk-assessment-v1",
                }
            )
    if batch_run:
        rows.append({"tool": "Batch Impact", "provider": batch_run.provider, "model": batch_run.model, "prompt_version": "batch-impact-rules-v1"})
    if war_room_run:
        rows.append({"tool": "Quality War Room", "provider": war_room_run.provider, "model": war_room_run.model, "prompt_version": "quality-war-room-rules-v1"})
    return rows


def _fields(*items: tuple[str, Any]) -> list[BriefField]:
    return [BriefField(label=label, value=_display(value)) for label, value in items]


def build_complaint_brief(db: Session, *, complaint_id: str) -> ComplaintBrief:
    complaint = ComplaintRepository(db).get_required(complaint_id)
    version = ComplaintVersionRepository(db).get_latest_for_complaint(complaint_id)
    if version is None:
        raise PharmaQSentinelError("Inspection brief requires a saved immutable complaint version", status_code=409)
    snapshot = version.snapshot
    snapshot_complaint = snapshot.get("complaint") or {}
    official_fields = snapshot_complaint.get("official_fields") or {}
    draft_id = snapshot_complaint.get("committed_from_draft_id") or complaint.committed_from_draft_id
    generated_at = utc_now()

    source_documents = _source_documents(db, draft_id, snapshot)
    evidence = _evidence_rows(db, draft_id, official_fields)
    corrections = _user_corrections(db, draft_id, complaint.id)
    risk_rows = _risk_rows(db, draft_id, complaint, snapshot)
    batch_run = _latest_for_draft(db, BatchImpactRun, draft_id, BatchImpactRun.created_at) if draft_id else None
    duplicate_run = _latest_for_draft(db, DuplicateAnalysisRun, draft_id, DuplicateAnalysisRun.created_at) if draft_id else None
    playbook_run = _latest_for_draft(db, InvestigationPlaybookRun, draft_id, InvestigationPlaybookRun.created_at) if draft_id else None
    war_room_run = _latest_for_draft(db, QualityWarRoomRun, draft_id, QualityWarRoomRun.started_at) if draft_id else None
    timeline = _audit_rows(db, complaint)
    provider_rows = _provider_rows(risk_rows=risk_rows, batch_run=batch_run, war_room_run=war_room_run)

    sections = [
        ReportSection(
            title="Report Title And Disclaimer",
            fields=_fields(
                ("Title", "Inspection-Ready Complaint Brief"),
                ("Disclaimer", INSPECTION_BRIEF_DISCLAIMER),
            ),
        ),
        ReportSection(
            title="Complaint Identification",
            fields=_fields(
                ("Complaint Number", complaint.complaint_number),
                ("Complaint ID", complaint.id),
                ("Status", complaint.status),
                ("Version", version.version_number),
                ("Committed At", complaint.committed_at),
            ),
        ),
        ReportSection(
            title="Origin And Customer Information",
            fields=_fields(
                ("Complaint Source", official_fields.get("complaint_source")),
                ("Customer Name", official_fields.get("customer_name")),
                ("Customer Contact", official_fields.get("customer_contact")),
                ("Country/Market", official_fields.get("country_market")),
            ),
        ),
        ReportSection(
            title="Product And Batch Information",
            fields=_fields(
                ("Product Type", official_fields.get("product_type")),
                ("Product Name", official_fields.get("product_name")),
                ("Strength/Grade", official_fields.get("product_strength_grade")),
                ("Dosage Form", official_fields.get("dosage_form")),
                ("Batch/Lot", official_fields.get("batch_lot_number")),
                ("Manufacturing Date", official_fields.get("manufacturing_date")),
                ("Expiry/Retest Date", official_fields.get("expiry_retest_date")),
                ("Quantity Affected", official_fields.get("quantity_affected")),
                ("Quantity Unit", official_fields.get("quantity_unit")),
            ),
        ),
        ReportSection(title="Complaint Narrative", fields=_fields(("Detailed Description", official_fields.get("detailed_description")))),
        ReportSection(
            title="Classification",
            fields=_fields(
                ("Complaint Type", official_fields.get("complaint_type")),
                ("Suggested Severity", official_fields.get("suggested_severity")),
                ("Suggested Priority", official_fields.get("suggested_priority")),
                ("Risk Confidence", official_fields.get("risk_confidence")),
            ),
        ),
        ReportSection(title="Original Source Documents", rows=[item.model_dump(mode="json") for item in source_documents]),
        ReportSection(title="Field-Level Evidence", rows=[item.model_dump(mode="json") for item in evidence]),
        ReportSection(title="User Corrections", rows=corrections, notes=["Rows include correction-like audit events and field-level patch events."]),
        ReportSection(title="Missing Information", rows=[{"item": _display(item)} for item in (snapshot.get("missing_information") or [])]),
        ReportSection(title="Initial And Latest Risk Assessments", rows=risk_rows),
        ReportSection(
            title="Safety-Routing Signals",
            fields=_fields(
                ("Safety Route", snapshot.get("safety_route") or official_fields.get("safety_route")),
                ("Adverse Event Signal", official_fields.get("adverse_event_signal")),
                ("Counterfeit Signal", official_fields.get("counterfeit_signal")),
                ("Patient Consumed Product", official_fields.get("patient_consumed_product")),
            ),
        ),
        ReportSection(title="Duplicate And Recurrence Results", rows=(duplicate_run.result_json if duplicate_run else {"status": "Not available"}).get("candidates", []) if duplicate_run else [], notes=(duplicate_run.result_json.get("limitations", []) if duplicate_run else ["No duplicate analysis run is linked to this saved draft."])),
        ReportSection(title="Batch Blast-Radius Summary", rows=[batch_run.summary_json] if batch_run else [], notes=batch_run.limitations_json.get("limitations", []) if batch_run and isinstance(batch_run.limitations_json, dict) else ["No Batch Impact run is linked to this saved draft."]),
        ReportSection(title="Containment Simulation Summary", notes=["No persisted containment simulation is available for this complaint. Simulation results are not currently stored."]),
        ReportSection(title="Quality War Room Consensus", rows=[war_room_run.consensus_json] if war_room_run else [], notes=["No Quality War Room run is linked to this saved draft."] if not war_room_run else []),
        ReportSection(title="Auditor-Rejected Unsupported Claims", rows=[{"claim": item} for item in ((war_room_run.auditor_output_json or {}).get("rejected_claims", []) if war_room_run else [])]),
        ReportSection(title="Investigation Playbook", rows=[playbook_run.playbook_json] if playbook_run else [], notes=["No investigation playbook run is linked to this saved draft."] if not playbook_run else []),
        ReportSection(title="Root-Cause Hypotheses", rows=(playbook_run.playbook_json.get("root_cause_hypotheses", []) if playbook_run else [])),
        ReportSection(title="CAPA Considerations", rows=[playbook_run.playbook_json.get("CAPA_considerations", {})] if playbook_run else [], notes=["CAPA content is suggestion-only and does not create an official CAPA."]),
        ReportSection(
            title="Human Review Details",
            fields=_fields(
                ("Committed By", complaint.committed_by),
                ("Review Meaning", complaint.review_meaning),
                ("Missing Information Acknowledged", complaint.missing_information_acknowledged),
                ("Change Reason", version.change_reason),
            ),
        ),
        ReportSection(title="Complete Audit Timeline", rows=timeline),
        ReportSection(title="Provider, Model And Prompt Versions", rows=provider_rows),
        ReportSection(
            title="Data And AI Limitations",
            notes=[
                "AI recommendations are draft decision support and require authorised QA review.",
                "Seeded pharmaceutical records are fictional demonstration data.",
                "This report is generated from the saved complaint version snapshot plus linked append-only records.",
                "PDF rendering uses safe standard fonts; unsupported glyphs may be represented as Unicode code point placeholders.",
            ],
        ),
        ReportSection(title="Complaint Snapshot Checksum", fields=_fields(("SHA-256", version.checksum))),
        ReportSection(title="Report Generation Timestamp", fields=_fields(("Generated At", generated_at))),
    ]

    base_payload = {
        "complaint_id": complaint.id,
        "complaint_number": complaint.complaint_number,
        "version_number": version.version_number,
        "snapshot_checksum": version.checksum,
        "sections": [section.model_dump(mode="json") for section in sections],
        "generated_at": _json_value(generated_at),
    }
    report_checksum = sha256_hexdigest(base_payload)
    return ComplaintBrief(
        report_id=f"brief-{complaint.complaint_number}-v{version.version_number}",
        title="Inspection-Ready Complaint Brief",
        disclaimer=INSPECTION_BRIEF_DISCLAIMER,
        complaint_id=complaint.id,
        complaint_number=complaint.complaint_number,
        version_number=version.version_number,
        document_identifier=f"{complaint.complaint_number}-BRIEF-v{version.version_number}",
        generated_at=generated_at,
        snapshot_checksum=version.checksum,
        report_checksum=report_checksum,
        source_documents=source_documents,
        field_evidence=evidence,
        user_corrections=corrections,
        sections=sections,
        limitations=[
            "Not a regulatory submission.",
            "Not a validated or 21 CFR Part 11 compliant record by itself.",
            "Requires authorised quality review and approval.",
        ],
    )
