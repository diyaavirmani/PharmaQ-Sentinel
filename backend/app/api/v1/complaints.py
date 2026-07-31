from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import ComplaintRepository, ComplaintVersionRepository, Pagination
from app.schemas.complaints import (
    ComplaintLedgerListResponse,
    ComplaintResponse,
    ComplaintVersionResponse,
)
from app.schemas.evidence import TimelineEntryResponse, TimelineListResponse
from app.services.complaint_save import complaint_timeline

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.get("", response_model=ComplaintLedgerListResponse)
def list_complaints(
    db: Annotated[Session, Depends(get_db)],
    complaint_number: Annotated[str | None, Query(max_length=40)] = None,
    product_name: Annotated[str | None, Query(max_length=255)] = None,
    batch_number: Annotated[str | None, Query(max_length=150)] = None,
    customer: Annotated[str | None, Query(max_length=255)] = None,
    complaint_type: Annotated[str | None, Query(max_length=150)] = None,
    severity: Annotated[str | None, Query(max_length=30)] = None,
    status: Annotated[str | None, Query(max_length=40)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ComplaintLedgerListResponse:
    pagination = Pagination(limit=limit, offset=offset)
    items = ComplaintRepository(db).list(
        pagination=pagination,
        complaint_number=complaint_number,
        product_name=product_name,
        batch_number=batch_number,
        customer=customer,
        complaint_type=complaint_type,
        severity=severity,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return ComplaintLedgerListResponse(
        items=[ComplaintResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        next_offset=offset + limit if len(items) == limit else None,
    )


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ComplaintResponse:
    return ComplaintResponse.model_validate(ComplaintRepository(db).get_required(complaint_id))


@router.get("/{complaint_id}/versions", response_model=list[ComplaintVersionResponse])
def list_complaint_versions(
    complaint_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[ComplaintVersionResponse]:
    ComplaintRepository(db).get_required(complaint_id)
    versions = ComplaintVersionRepository(db).list_for_complaint(complaint_id)
    return [ComplaintVersionResponse.model_validate(version) for version in versions]


@router.get("/{complaint_id}/timeline", response_model=TimelineListResponse)
def list_complaint_timeline(
    complaint_id: str,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TimelineListResponse:
    items = [TimelineEntryResponse.model_validate(item) for item in complaint_timeline(db, complaint_id=complaint_id)]
    paged = items[offset: offset + limit]
    return TimelineListResponse(
        items=paged,
        limit=limit,
        offset=offset,
        next_offset=offset + limit if offset + limit < len(items) else None,
    )
