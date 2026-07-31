from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BatchImpactRun, ComplaintDraft, FieldEvidence, RiskAssessmentVersion
from app.repositories.complaint_drafts import ComplaintDraftRepository


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _draft_snapshot(draft: ComplaintDraft) -> dict[str, Any]:
    fields = [
        "id",
        "thread_id",
        "status",
        "complaint_source",
        "customer_name",
        "country_market",
        "product_type",
        "product_name",
        "product_strength_grade",
        "dosage_form",
        "batch_lot_number",
        "manufacturing_date",
        "expiry_retest_date",
        "quantity_affected",
        "quantity_unit",
        "complaint_type",
        "complaint_date",
        "detailed_description",
        "sample_available",
        "patient_consumed_product",
        "adverse_event_signal",
        "counterfeit_signal",
        "storage_conditions",
        "suggested_severity",
        "suggested_priority",
        "safety_route",
        "risk_rationale",
        "potential_hazard",
        "suggested_next_action",
        "risk_confidence",
        "missing_fields",
    ]
    return {field: _json_value(getattr(draft, field)) for field in fields}


def _evidence_index(db: Session, draft_id: str) -> list[dict[str, Any]]:
    statement = (
        select(FieldEvidence)
        .where(FieldEvidence.draft_id == draft_id, FieldEvidence.is_active.is_(True))
        .order_by(FieldEvidence.created_at.asc())
    )
    return [
        {
            "evidence_id": evidence.id,
            "field_name": evidence.field_name,
            "evidence_type": evidence.evidence_type,
            "confidence": _json_value(evidence.confidence),
            "source_excerpt": evidence.source_excerpt,
            "is_explicit": evidence.is_explicit,
        }
        for evidence in db.scalars(statement).all()
    ]


def _latest_risk(db: Session, draft_id: str) -> dict[str, Any] | None:
    statement = (
        select(RiskAssessmentVersion)
        .where(RiskAssessmentVersion.draft_id == draft_id)
        .order_by(RiskAssessmentVersion.version_number.desc())
    )
    risk = db.scalars(statement).first()
    if risk is None:
        return None
    return {
        "version_number": risk.version_number,
        "severity": risk.severity,
        "priority": risk.priority,
        "safety_route": risk.safety_route,
        "risk_rationale": risk.risk_rationale,
        "confidence": _json_value(risk.confidence),
        "supporting_evidence": risk.supporting_evidence,
        "contradicting_evidence": risk.contradicting_evidence,
    }


def _latest_batch_impact(db: Session, draft_id: str) -> dict[str, Any] | None:
    statement = (
        select(BatchImpactRun)
        .where(BatchImpactRun.draft_id == draft_id)
        .order_by(BatchImpactRun.created_at.desc())
    )
    run = db.scalars(statement).first()
    if run is None:
        return None
    return {
        "run_id": run.id,
        "summary": run.summary_json,
        "signals": run.signals_json,
        "limitations": run.limitations_json,
    }


def build_quality_war_room_context(db: Session, draft_id: str) -> dict[str, Any]:
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    complaint = _draft_snapshot(draft)
    evidence = _evidence_index(db, draft_id)
    risk = _latest_risk(db, draft_id)
    batch_impact = _latest_batch_impact(db, draft_id)
    public_complaint = {key: value for key, value in complaint.items() if key not in {"customer_contact"}}
    packaging_complaint = {
        key: value
        for key, value in public_complaint.items()
        if key not in {"patient_consumed_product", "adverse_event_signal"}
    }
    pv_complaint = {
        key: public_complaint.get(key)
        for key in (
            "id",
            "complaint_type",
            "detailed_description",
            "patient_consumed_product",
            "adverse_event_signal",
            "safety_route",
            "suggested_severity",
        )
    }
    return {
        "input_snapshot": {
            "complaint": public_complaint,
            "evidence_ids": [item["evidence_id"] for item in evidence],
            "risk_version": risk.get("version_number") if risk else None,
            "batch_impact_run_id": batch_impact.get("run_id") if batch_impact else None,
        },
        "complaint": public_complaint,
        "evidence_index": evidence,
        "risk_assessment": risk,
        "batch_impact_summary": batch_impact,
        "specialist_contexts": {
            "qa": {"complaint": public_complaint, "evidence_index": evidence, "risk_assessment": risk},
            "manufacturing": {"complaint": public_complaint, "batch_impact_summary": batch_impact},
            "packaging": {"complaint": packaging_complaint, "batch_impact_summary": batch_impact},
            "pv": {"complaint": pv_complaint, "evidence_index": evidence},
        },
    }
