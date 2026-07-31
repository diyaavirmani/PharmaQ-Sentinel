from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.complaint_drafts import ComplaintDraftRepository
from app.repositories.investigation import (
    InvestigationPlaybookRunRepository,
    InvestigationReviewActionRepository,
)
from app.services.investigation.capa_recommender import capa_considerations
from app.services.investigation.playbook_registry import playbook_steps, resolve_category
from app.services.investigation.schemas import (
    InvestigationPlaybookResult,
    InvestigationReviewActionRequest,
)


def _serialise(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    return value


def create_investigation_playbook(
    db: Session,
    *,
    draft_id: str,
    created_by: str | None,
) -> InvestigationPlaybookResult:
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    category = resolve_category(draft.complaint_type, draft.detailed_description)
    containment, checklist, hypotheses = playbook_steps(category)
    result = InvestigationPlaybookResult(
        run_id="pending",
        draft_id=draft.id,
        category=category,
        immediate_containment=containment,
        investigation_checklist=checklist,
        root_cause_hypotheses=hypotheses,
        CAPA_considerations=capa_considerations(category),
        limitations=[
            "Potential root-cause language is hypothesis-only.",
            "No CAPA, severity, regulatory route or quality conclusion is authorized by this playbook.",
            "Seeded connected records are fictional demonstration data.",
        ],
    )
    run = InvestigationPlaybookRunRepository(db).append(
        draft_id=draft.id,
        input_snapshot={
            "product_name": draft.product_name,
            "batch_lot_number": draft.batch_lot_number,
            "complaint_type": draft.complaint_type,
            "detailed_description": draft.detailed_description,
            "complaint_date": _serialise(draft.complaint_date),
        },
        playbook_json=result.model_dump(mode="json"),
        status="COMPLETE",
        created_by=created_by,
    )
    result.run_id = run.id
    run.playbook_json = result.model_dump(mode="json")
    db.flush()
    return result


def record_review_action(db: Session, *, draft_id: str, request: InvestigationReviewActionRequest):
    ComplaintDraftRepository(db).get_required(draft_id)
    return InvestigationReviewActionRepository(db).append(
        draft_id=draft_id,
        run_id=request.run_id,
        action_type=request.action_type,
        target_type=request.target_type,
        target_id=request.target_id,
        original_text_json=request.original_text,
        saved_text=request.saved_text,
        reason=request.reason,
        actor_identifier=request.actor_identifier,
    )
