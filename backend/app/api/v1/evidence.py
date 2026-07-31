from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import Pagination
from app.schemas.evidence import (
    FieldEvidenceDetailResponse,
    FieldEvidenceListResponse,
    TimelineListResponse,
)
from app.services import evidence_lock

router = APIRouter(prefix="/complaint-drafts", tags=["evidence"])


@router.get("/{draft_id}/evidence", response_model=FieldEvidenceListResponse)
def list_complaint_evidence(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
    field_name: Annotated[str | None, Query(max_length=150)] = None,
    active_only: Annotated[bool, Query()] = False,
    evidence_type: Annotated[str | None, Query(max_length=40)] = None,
    attachment_id: Annotated[str | None, Query(max_length=36)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FieldEvidenceListResponse:
    return evidence_lock.list_evidence(
        db,
        draft_id=draft_id,
        field_name=field_name,
        active_only=active_only,
        evidence_type=evidence_type,
        attachment_id=attachment_id,
        pagination=Pagination(limit=limit, offset=offset),
    )


@router.get("/{draft_id}/evidence/{field_name}", response_model=FieldEvidenceDetailResponse)
def get_complaint_field_evidence(
    draft_id: str,
    field_name: str,
    db: Annotated[Session, Depends(get_db)],
) -> FieldEvidenceDetailResponse:
    return evidence_lock.get_field_evidence_detail(db, draft_id=draft_id, field_name=field_name)


@router.get("/{draft_id}/timeline", response_model=TimelineListResponse)
def list_complaint_timeline(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[str | None, Query(max_length=40)] = None,
    event_type: Annotated[str | None, Query(max_length=100)] = None,
    field_name: Annotated[str | None, Query(max_length=150)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TimelineListResponse:
    return evidence_lock.list_timeline(
        db,
        draft_id=draft_id,
        actor=actor,
        event_type=event_type,
        field_name=field_name,
        pagination=Pagination(limit=limit, offset=offset),
    )
