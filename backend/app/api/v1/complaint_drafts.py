from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
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
from app.services.complaint_save import save_complaint

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
