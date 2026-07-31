from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import ComplaintDraft, HistoricalComplaint
from app.repositories.base import Pagination
from app.repositories.complaint_drafts import ComplaintDraftRepository
from app.repositories.complaint_intelligence import (
    DuplicateAnalysisRunRepository,
    DuplicateCandidateRepository,
)
from app.services.complaint_intelligence.recurrence_detector import recurrence_signals_for
from app.services.complaint_intelligence.schemas import (
    DuplicateAnalysisResult,
    DuplicateCandidateResult,
)
from app.services.complaint_intelligence.score_explainer import classify, recommended_action
from app.services.complaint_intelligence.similarity import cosine_text_similarity


def _serialise(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _snapshot(draft: ComplaintDraft) -> dict[str, Any]:
    fields = (
        "id",
        "product_name",
        "batch_lot_number",
        "customer_name",
        "complaint_type",
        "complaint_date",
        "quantity_affected",
        "detailed_description",
        "suggested_severity",
        "adverse_event_signal",
        "counterfeit_signal",
    )
    return {field: _serialise(getattr(draft, field)) for field in fields}


def _date_distance(left: date | None, right: date | None) -> int | None:
    if left is None or right is None:
        return None
    return abs((left - right).days)


def _candidate_batch_number(candidate: HistoricalComplaint) -> str | None:
    return candidate.batch.batch_number if candidate.batch else None


def _same_shared_context(draft_batch_number: str | None, candidate: HistoricalComplaint) -> tuple[int, list[str], list[str]]:
    score = 0
    reasons: list[str] = []
    fields: list[str] = []
    if not draft_batch_number or not candidate.batch:
        return score, reasons, fields
    if candidate.batch.batch_number == draft_batch_number:
        score += 25
        reasons.append("Same batch number.")
        fields.append("batch_lot_number")
    if candidate.batch.packaging_material_lots:
        score += 5
        reasons.append("Candidate has packaging-lot context available.")
        fields.append("packaging_material_lots")
    if candidate.batch.material_lots:
        score += 4
        reasons.append("Candidate has raw-material lot context available.")
        fields.append("material_lots")
    if candidate.batch.equipment_records:
        score += 3
        reasons.append("Candidate has equipment context available.")
        fields.append("equipment")
    return score, reasons, fields


def _score_candidate(draft: ComplaintDraft, candidate: HistoricalComplaint) -> DuplicateCandidateResult:
    score = 0
    reasons: list[str] = []
    matching_fields: list[str] = []
    contradicting_fields: list[str] = []

    if draft.complaint_source and draft.complaint_source == candidate.complaint_number:
        score += 45
        reasons.append("External/source complaint reference matches candidate complaint number.")
        matching_fields.append("complaint_source")
    if candidate.product and draft.product_name and candidate.product.product_name == draft.product_name:
        score += 15
        reasons.append("Same product name.")
        matching_fields.append("product_name")
    elif candidate.product and draft.product_name:
        contradicting_fields.append("product_name")
    batch_score, batch_reasons, batch_fields = _same_shared_context(draft.batch_lot_number, candidate)
    score += batch_score
    reasons.extend(batch_reasons)
    matching_fields.extend(batch_fields)
    if draft.customer_name and candidate.customer_name and draft.customer_name.lower() == candidate.customer_name.lower():
        score += 10
        reasons.append("Same customer name.")
        matching_fields.append("customer_name")
    if draft.complaint_type and draft.complaint_type == candidate.complaint_type:
        score += 15
        reasons.append("Same complaint type.")
        matching_fields.append("complaint_type")
    elif draft.complaint_type:
        contradicting_fields.append("complaint_type")
    distance = _date_distance(draft.complaint_date, candidate.complaint_date)
    if distance is not None and distance <= 7:
        score += 10
        reasons.append("Complaint dates are within seven days.")
        matching_fields.append("complaint_date")
    text_similarity = cosine_text_similarity(draft.detailed_description, candidate.detailed_description)
    if text_similarity >= 0.35:
        score += min(15, int(text_similarity * 15))
        reasons.append("Complaint descriptions are textually similar.")
        matching_fields.append("detailed_description")
    recurrence = bool(draft.complaint_type and draft.complaint_type == candidate.complaint_type and draft.product_name)
    total = min(score, 100)
    classification = classify(total, recurrence=recurrence)
    return DuplicateCandidateResult(
        candidate_complaint_id=candidate.id,
        complaint_number=candidate.complaint_number,
        classification=classification,
        total_score=total,
        reasons=reasons or ["Low deterministic similarity."],
        matching_fields=sorted(set(matching_fields)),
        contradicting_fields=sorted(set(contradicting_fields)),
        evidence_references=[candidate.id],
        date_distance_days=distance,
        text_similarity=f"{text_similarity:.4f}",
        recommended_user_action=recommended_action(classification),
    )


def run_duplicate_analysis(
    db: Session,
    *,
    draft_id: str,
    created_by: str | None,
) -> DuplicateAnalysisResult:
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    candidates = DuplicateCandidateRepository(db).list_historical_candidates(Pagination(limit=200, offset=0))
    scored = [_score_candidate(draft, candidate) for candidate in candidates]
    visible = [candidate for candidate in scored if candidate.classification != "UNRELATED"]
    visible.sort(key=lambda candidate: candidate.total_score, reverse=True)
    recurrence = recurrence_signals_for(draft=draft, candidates=candidates)
    result = DuplicateAnalysisResult(
        run_id="pending",
        draft_id=draft.id,
        candidates=visible[:20],
        recurrence_signals=recurrence,
        limitations=[
            "Deterministic similarity is decision support only.",
            "Small seeded demo dataset may understate or overstate recurrence signals.",
            "QA must review source records before marking a complaint duplicate.",
        ],
    )
    run = DuplicateAnalysisRunRepository(db).append(
        draft_id=draft.id,
        input_snapshot=_snapshot(draft),
        result_json=result.model_dump(mode="json"),
        status="COMPLETE",
        created_by=created_by,
    )
    result.run_id = run.id
    run.result_json = result.model_dump(mode="json")
    db.flush()
    return result
