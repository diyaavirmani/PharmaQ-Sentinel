from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.reference import (
    BatchReferenceResponse,
    HistoricalComplaintResponse,
    ProductReferenceResponse,
    SeedStatusResponse,
)
from app.services import reference as reference_service

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/products", response_model=list[ProductReferenceResponse])
def products(db: Annotated[Session, Depends(get_db)]) -> list[ProductReferenceResponse]:
    return reference_service.list_products(db)


@router.get("/batches/{batch_number}", response_model=BatchReferenceResponse)
def batch_reference(
    batch_number: str,
    db: Annotated[Session, Depends(get_db)],
) -> BatchReferenceResponse:
    return reference_service.get_batch_reference(db, batch_number)


@router.get("/seed-status", response_model=SeedStatusResponse)
def seed_status(db: Annotated[Session, Depends(get_db)]) -> SeedStatusResponse:
    return reference_service.get_seed_status(db)


@router.get("/historical-complaints", response_model=list[HistoricalComplaintResponse])
def historical_complaints(
    db: Annotated[Session, Depends(get_db)],
    product_id: str | None = None,
    batch_number: str | None = None,
    complaint_type: str | None = None,
    severity: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[HistoricalComplaintResponse]:
    return reference_service.list_historical_complaints(
        db,
        product_id=product_id,
        batch_number=batch_number,
        complaint_type=complaint_type,
        severity=severity,
        limit=limit,
        offset=offset,
    )
