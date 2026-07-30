from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.base import Pagination, RepositoryNotFoundError
from app.repositories.reference import (
    BatchRepository,
    HistoricalComplaintRepository,
    ProductRepository,
    ReferenceCountRepository,
)
from app.schemas.reference import (
    BatchReferenceResponse,
    DeviationReference,
    DistributionRecordReference,
    DistributionSummary,
    EquipmentReference,
    HistoricalComplaintResponse,
    ManufacturingLineReference,
    MaterialLotReference,
    PackagingMaterialLotReference,
    ProductReferenceResponse,
    SeedStatusResponse,
    WarehouseInventoryReference,
)


def list_products(db: Session) -> list[ProductReferenceResponse]:
    products = ProductRepository(db).list()
    return [ProductReferenceResponse.model_validate(product) for product in products]


def get_batch_reference(db: Session, batch_number: str) -> BatchReferenceResponse:
    batch = BatchRepository(db).get_by_batch_number(batch_number)
    if batch is None:
        raise RepositoryNotFoundError("Batch", batch_number)

    total_distributed = sum(
        (record.quantity_distributed for record in batch.distribution_records),
        start=Decimal("0.000"),
    )

    return BatchReferenceResponse(
        id=batch.id,
        batch_number=batch.batch_number,
        manufacturing_date=batch.manufacturing_date,
        expiry_retest_date=batch.expiry_retest_date,
        status=batch.status,
        quantity_manufactured=batch.quantity_manufactured,
        quantity_released=batch.quantity_released,
        is_demo=batch.is_demo,
        product=ProductReferenceResponse.model_validate(batch.product),
        manufacturing_line=(
            ManufacturingLineReference.model_validate(batch.manufacturing_line)
            if batch.manufacturing_line
            else None
        ),
        packaging_line=(
            ManufacturingLineReference.model_validate(batch.packaging_line)
            if batch.packaging_line
            else None
        ),
        material_lots=[MaterialLotReference.model_validate(lot) for lot in batch.material_lots],
        packaging_material_lots=[
            PackagingMaterialLotReference.model_validate(lot) for lot in batch.packaging_material_lots
        ],
        equipment=[EquipmentReference.model_validate(record) for record in batch.equipment_records],
        deviations=[DeviationReference.model_validate(deviation) for deviation in batch.deviations],
        distribution_summary=DistributionSummary(
            total_quantity_distributed=total_distributed,
            records=[
                DistributionRecordReference.model_validate(record)
                for record in batch.distribution_records
            ],
        ),
        warehouse_inventory=[
            WarehouseInventoryReference.model_validate(record) for record in batch.warehouse_inventory
        ],
    )


def get_seed_status(db: Session) -> SeedStatusResponse:
    return SeedStatusResponse(**ReferenceCountRepository(db).seed_status_counts())


def list_historical_complaints(
    db: Session,
    *,
    product_id: str | None,
    batch_number: str | None,
    complaint_type: str | None,
    severity: str | None,
    limit: int,
    offset: int,
) -> list[HistoricalComplaintResponse]:
    complaints = HistoricalComplaintRepository(db).list_filtered(
        product_id=product_id,
        batch_number=batch_number,
        complaint_type=complaint_type,
        severity=severity,
        pagination=Pagination(limit=limit, offset=offset),
    )
    return [
        HistoricalComplaintResponse(
            id=complaint.id,
            complaint_number=complaint.complaint_number,
            product_id=complaint.product_id,
            batch_id=complaint.batch_id,
            product_name=complaint.product.product_name if complaint.product else None,
            batch_number=complaint.batch.batch_number if complaint.batch else None,
            customer_name=complaint.customer_name,
            complaint_type=complaint.complaint_type,
            detailed_description=complaint.detailed_description,
            severity=complaint.severity,
            complaint_date=complaint.complaint_date,
            status=complaint.status,
            is_demo=complaint.is_demo,
        )
        for complaint in complaints
    ]
