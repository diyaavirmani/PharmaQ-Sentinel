from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import (
    CAPA,
    Batch,
    Deviation,
    DistributionRecord,
    Equipment,
    HistoricalComplaint,
    MaterialLot,
    PackagingMaterialLot,
    Product,
    Supplier,
    WarehouseInventory,
)
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class ProductRepository(BaseRepository[Product]):
    entity_name = "Product"

    def get(self, product_id: str) -> Product | None:
        return self.db.get(Product, product_id)

    def get_by_code(self, product_code: str) -> Product | None:
        statement = select(Product).where(Product.product_code == product_code)
        return self.db.scalars(statement).first()

    def list(self, pagination: Pagination | None = None) -> list[Product]:
        statement = select(Product).order_by(Product.product_name.asc())
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())


class BatchRepository(BaseRepository[Batch]):
    entity_name = "Batch"

    def get(self, batch_id: str) -> Batch | None:
        return self.db.get(Batch, batch_id)

    def get_by_batch_number(self, batch_number: str) -> Batch | None:
        statement = (
            select(Batch)
            .options(
                selectinload(Batch.product),
                selectinload(Batch.manufacturing_line),
                selectinload(Batch.packaging_line),
                selectinload(Batch.material_lots).selectinload(MaterialLot.supplier),
                selectinload(Batch.packaging_material_lots).selectinload(PackagingMaterialLot.supplier),
                selectinload(Batch.equipment_records),
                selectinload(Batch.deviations).selectinload(Deviation.capas),
                selectinload(Batch.distribution_records),
                selectinload(Batch.warehouse_inventory),
            )
            .where(Batch.batch_number == batch_number)
        )
        return self.db.scalars(statement).first()

    def list(self, pagination: Pagination | None = None) -> list[Batch]:
        statement = select(Batch).order_by(Batch.batch_number.asc())
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())


class HistoricalComplaintRepository(BaseRepository[HistoricalComplaint]):
    entity_name = "HistoricalComplaint"

    def list_filtered(
        self,
        *,
        product_id: str | None = None,
        batch_number: str | None = None,
        complaint_type: str | None = None,
        severity: str | None = None,
        pagination: Pagination | None = None,
    ) -> list[HistoricalComplaint]:
        statement = (
            select(HistoricalComplaint)
            .options(selectinload(HistoricalComplaint.product), selectinload(HistoricalComplaint.batch))
            .order_by(HistoricalComplaint.complaint_date.desc(), HistoricalComplaint.complaint_number.asc())
        )
        if product_id is not None:
            statement = statement.where(HistoricalComplaint.product_id == product_id)
        if batch_number is not None:
            statement = statement.join(HistoricalComplaint.batch).where(Batch.batch_number == batch_number)
        if complaint_type is not None:
            statement = statement.where(HistoricalComplaint.complaint_type == complaint_type)
        if severity is not None:
            statement = statement.where(HistoricalComplaint.severity == severity)
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())


class ReferenceCountRepository(BaseRepository[object]):
    def seed_status_counts(self) -> dict[str, int]:
        return {
            "products": self.db.scalar(select(func.count()).select_from(Product)) or 0,
            "batches": self.db.scalar(select(func.count()).select_from(Batch)) or 0,
            "suppliers": self.db.scalar(select(func.count()).select_from(Supplier)) or 0,
            "materials": self.db.scalar(select(func.count()).select_from(MaterialLot)) or 0,
            "packaging_materials": self.db.scalar(select(func.count()).select_from(PackagingMaterialLot)) or 0,
            "equipment": self.db.scalar(select(func.count()).select_from(Equipment)) or 0,
            "deviations": self.db.scalar(select(func.count()).select_from(Deviation)) or 0,
            "capas": self.db.scalar(select(func.count()).select_from(CAPA)) or 0,
            "historical_complaints": self.db.scalar(select(func.count()).select_from(HistoricalComplaint)) or 0,
            "distribution_records": self.db.scalar(select(func.count()).select_from(DistributionRecord)) or 0,
            "warehouse_inventory": self.db.scalar(select(func.count()).select_from(WarehouseInventory)) or 0,
        }
