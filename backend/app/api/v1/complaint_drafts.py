from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.quality_war_room import run_quality_war_room
from app.agents.quality_war_room.schemas import (
    QualityWarRoomRunRequest,
    QualityWarRoomRunResponse,
    QualityWarRoomRunStartedResponse,
)
from app.core.database import get_db
from app.repositories.base import Pagination
from app.repositories.complaint_drafts import ComplaintDraftRepository
from app.repositories.complaint_intelligence import DuplicateAnalysisRunRepository
from app.repositories.investigation import InvestigationPlaybookRunRepository
from app.repositories.quality_war_room import (
    QualityWarRoomEventRepository,
    QualityWarRoomRunRepository,
)
from app.schemas.complaints import (
    ComplaintDraftCreateRequest,
    ComplaintDraftDevelopmentPatchRequest,
    ComplaintDraftResponse,
    ComplaintDraftStatusResponse,
    ComplaintResponse,
    SaveComplaintRequest,
)
from app.services import complaint_drafts as draft_service
from app.services.batch_impact import build_batch_impact_analysis, simulate_containment_scope
from app.services.batch_impact.schemas import (
    BatchImpactResponse,
    BatchImpactRunRequest,
    ContainmentSimulationRequest,
    ContainmentSimulationResponse,
)
from app.services.complaint_intelligence import run_duplicate_analysis
from app.services.complaint_intelligence.schemas import (
    DuplicateAnalysisResult,
    DuplicateAnalysisRunResponse,
    IntelligenceRunRequest,
)
from app.services.complaint_save import save_complaint
from app.services.investigation import create_investigation_playbook
from app.services.investigation.playbook_engine import record_review_action
from app.services.investigation.schemas import (
    InvestigationPlaybookResult,
    InvestigationPlaybookRunResponse,
    InvestigationReviewActionRequest,
    InvestigationReviewActionResponse,
)

router = APIRouter(prefix="/complaint-drafts", tags=["complaint-drafts"])


def _commit_or_rollback(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.post("", response_model=ComplaintDraftResponse, status_code=status.HTTP_201_CREATED)
def create_complaint_draft(
    request: ComplaintDraftCreateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ComplaintDraftResponse:
    try:
        draft = draft_service.create_empty_draft(db, created_by=request.created_by)
        _commit_or_rollback(db)
        db.refresh(draft)
        return ComplaintDraftResponse.model_validate(draft)
    except Exception:
        db.rollback()
        raise


@router.get("/{draft_id}", response_model=ComplaintDraftResponse)
def get_complaint_draft(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ComplaintDraftResponse:
    try:
        draft = draft_service.restore_draft(db, draft_id=draft_id)
        _commit_or_rollback(db)
        db.refresh(draft)
        return ComplaintDraftResponse.model_validate(draft)
    except Exception:
        db.rollback()
        raise


@router.post("/{draft_id}/reset", response_model=ComplaintDraftResponse)
def reset_complaint_draft(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ComplaintDraftResponse:
    try:
        draft = draft_service.reset_draft(db, draft_id=draft_id)
        _commit_or_rollback(db)
        db.refresh(draft)
        return ComplaintDraftResponse.model_validate(draft)
    except Exception:
        db.rollback()
        raise


@router.get("/{draft_id}/status", response_model=ComplaintDraftStatusResponse)
def get_complaint_draft_status(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ComplaintDraftStatusResponse:
    return draft_service.get_draft_status(db, draft_id=draft_id)


@router.patch("/{draft_id}/development-patch", response_model=ComplaintDraftResponse)
def development_patch_complaint_draft(
    draft_id: str,
    request: ComplaintDraftDevelopmentPatchRequest,
    db: Annotated[Session, Depends(get_db)],
    response: Response,
) -> ComplaintDraftResponse:
    try:
        draft = draft_service.apply_development_patch(db, draft_id=draft_id, request=request)
        _commit_or_rollback(db)
        db.refresh(draft)
        response.headers["X-PharmaQ-Development-Only"] = "true"
        return ComplaintDraftResponse.model_validate(draft)
    except Exception:
        db.rollback()
        raise


@router.post("/{draft_id}/save", response_model=ComplaintResponse)
def save_complaint_draft(
    draft_id: str,
    request: SaveComplaintRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ComplaintResponse:
    try:
        complaint = save_complaint(db, draft_id=draft_id, request=request)
        _commit_or_rollback(db)
        db.refresh(complaint)
        return ComplaintResponse.model_validate(complaint)
    except Exception:
        db.rollback()
        raise


@router.post("/{draft_id}/batch-impact", response_model=BatchImpactResponse)
def run_batch_impact(
    draft_id: str,
    request: BatchImpactRunRequest,
    db: Annotated[Session, Depends(get_db)],
) -> BatchImpactResponse:
    try:
        result = build_batch_impact_analysis(db, draft_id=draft_id, created_by=request.created_by)
        _commit_or_rollback(db)
        return result
    except Exception:
        db.rollback()
        raise


@router.post("/{draft_id}/batch-impact/simulate", response_model=ContainmentSimulationResponse)
def simulate_batch_impact(
    draft_id: str,
    request: ContainmentSimulationRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ContainmentSimulationResponse:
    return simulate_containment_scope(db, draft_id=draft_id, request=request)


@router.post(
    "/{draft_id}/quality-war-room/runs",
    response_model=QualityWarRoomRunStartedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quality_war_room_run(
    draft_id: str,
    _request: QualityWarRoomRunRequest,
    db: Annotated[Session, Depends(get_db)],
) -> QualityWarRoomRunStartedResponse:
    try:
        ComplaintDraftRepository(db).get_required(draft_id)
        run_id = run_quality_war_room(db, draft_id=draft_id)
        _commit_or_rollback(db)
        return QualityWarRoomRunStartedResponse(run_id=run_id, status="COMPLETE")
    except Exception:
        db.rollback()
        raise


@router.get("/{draft_id}/quality-war-room/runs", response_model=list[QualityWarRoomRunResponse])
def list_quality_war_room_runs(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[QualityWarRoomRunResponse]:
    ComplaintDraftRepository(db).get_required(draft_id)
    runs = QualityWarRoomRunRepository(db).list_for_draft(draft_id, Pagination(limit=50, offset=0))
    return [QualityWarRoomRunResponse.model_validate(run) for run in runs]


@router.get("/{draft_id}/quality-war-room/runs/{run_id}", response_model=QualityWarRoomRunResponse)
def get_quality_war_room_run(
    draft_id: str,
    run_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> QualityWarRoomRunResponse:
    ComplaintDraftRepository(db).get_required(draft_id)
    run = QualityWarRoomRunRepository(db).get_required(run_id)
    if run.draft_id != draft_id:
        from app.core.exceptions import PharmaQSentinelError

        raise PharmaQSentinelError("Quality War Room run not found for draft", status_code=404)
    run.events = sorted(run.events, key=lambda event: (event.created_at, event.id))
    return QualityWarRoomRunResponse.model_validate(run)


@router.get("/{draft_id}/quality-war-room/runs/{run_id}/stream")
def stream_quality_war_room_run(
    draft_id: str,
    run_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    ComplaintDraftRepository(db).get_required(draft_id)
    run = QualityWarRoomRunRepository(db).get_required(run_id)
    if run.draft_id != draft_id:
        from app.core.exceptions import PharmaQSentinelError

        raise PharmaQSentinelError("Quality War Room run not found for draft", status_code=404)
    events = QualityWarRoomEventRepository(db).list_for_run(run_id)

    def _generate():
        for event in events:
            payload = {
                "id": event.id,
                "event_type": event.event_type,
                "agent_name": event.agent_name,
                "status": event.status,
                "concise_message": event.concise_message,
                "evidence_ids": (event.evidence_ids_json or {}).get("evidence_ids", []),
                "created_at": event.created_at.isoformat(),
            }
            yield f"id: {event.id}\n"
            yield f"event: {event.event_type}\n"
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")


@router.post("/{draft_id}/duplicate-analysis", response_model=DuplicateAnalysisResult)
def create_duplicate_analysis(
    draft_id: str,
    request: IntelligenceRunRequest,
    db: Annotated[Session, Depends(get_db)],
) -> DuplicateAnalysisResult:
    try:
        result = run_duplicate_analysis(db, draft_id=draft_id, created_by=request.created_by)
        _commit_or_rollback(db)
        return result
    except Exception:
        db.rollback()
        raise


@router.get("/{draft_id}/duplicate-analysis/runs", response_model=list[DuplicateAnalysisRunResponse])
def list_duplicate_analysis_runs(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[DuplicateAnalysisRunResponse]:
    ComplaintDraftRepository(db).get_required(draft_id)
    runs = DuplicateAnalysisRunRepository(db).list_for_draft(draft_id, Pagination(limit=50, offset=0))
    return [DuplicateAnalysisRunResponse.model_validate(run) for run in runs]


@router.post("/{draft_id}/investigation-playbook", response_model=InvestigationPlaybookResult)
def create_playbook(
    draft_id: str,
    request: IntelligenceRunRequest,
    db: Annotated[Session, Depends(get_db)],
) -> InvestigationPlaybookResult:
    try:
        result = create_investigation_playbook(db, draft_id=draft_id, created_by=request.created_by)
        _commit_or_rollback(db)
        return result
    except Exception:
        db.rollback()
        raise


@router.get("/{draft_id}/investigation-playbook/runs", response_model=list[InvestigationPlaybookRunResponse])
def list_playbook_runs(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[InvestigationPlaybookRunResponse]:
    ComplaintDraftRepository(db).get_required(draft_id)
    runs = InvestigationPlaybookRunRepository(db).list_for_draft(draft_id, Pagination(limit=50, offset=0))
    return [InvestigationPlaybookRunResponse.model_validate(run) for run in runs]


@router.post("/{draft_id}/investigation-review-actions", response_model=InvestigationReviewActionResponse)
def create_investigation_review_action(
    draft_id: str,
    request: InvestigationReviewActionRequest,
    db: Annotated[Session, Depends(get_db)],
) -> InvestigationReviewActionResponse:
    try:
        action = record_review_action(db, draft_id=draft_id, request=request)
        _commit_or_rollback(db)
        db.refresh(action)
        return InvestigationReviewActionResponse.model_validate(action)
    except Exception:
        db.rollback()
        raise
