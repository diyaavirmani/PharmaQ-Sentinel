from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import CHAR, DATETIME, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MYSQL_TABLE_KWARGS, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ProductType, RecordSource

batch_material_lots = Table(
    "batch_material_lots",
    Base.metadata,
    Column(
        "batch_id",
        CHAR(36),
        ForeignKey("batches.id", name="fk_bml_batch", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column(
        "material_lot_id",
        CHAR(36),
        ForeignKey("material_lots.id", name="fk_bml_material_lot", ondelete="RESTRICT"),
        primary_key=True,
    ),
    UniqueConstraint("batch_id", "material_lot_id", name="uq_batch_material_lots_pair"),
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_ai_ci",
)

batch_packaging_material_lots = Table(
    "batch_packaging_material_lots",
    Base.metadata,
    Column(
        "batch_id",
        CHAR(36),
        ForeignKey("batches.id", name="fk_bpml_batch", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column(
        "packaging_material_lot_id",
        CHAR(36),
        ForeignKey("packaging_material_lots.id", name="fk_bpml_packaging_material_lot", ondelete="RESTRICT"),
        primary_key=True,
    ),
    UniqueConstraint(
        "batch_id",
        "packaging_material_lot_id",
        name="uq_batch_packaging_lots_pair",
    ),
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_ai_ci",
)

batch_equipment = Table(
    "batch_equipment",
    Base.metadata,
    Column(
        "batch_id",
        CHAR(36),
        ForeignKey("batches.id", name="fk_be_batch", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column(
        "equipment_id",
        CHAR(36),
        ForeignKey("equipment.id", name="fk_be_equipment", ondelete="RESTRICT"),
        primary_key=True,
    ),
    UniqueConstraint("batch_id", "equipment_id", name="uq_batch_equipment_pair"),
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_0900_ai_ci",
)


class DemoRecordMixin:
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    record_source: Mapped[str] = mapped_column(
        String(40),
        default=RecordSource.MANUAL_DEMO_SEED.value,
        nullable=False,
    )


class Product(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("product_code", name="uq_products_product_code"),
        Index("ix_products_product_name", "product_name"),
        Index("ix_products_product_type", "product_type"),
        MYSQL_TABLE_KWARGS,
    )

    product_code: Mapped[str] = mapped_column(String(80), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False, default=ProductType.UNKNOWN.value)
    strength_grade: Mapped[str | None] = mapped_column(String(150), nullable=True)
    dosage_form: Mapped[str | None] = mapped_column(String(100), nullable=True)
    market_status: Mapped[str | None] = mapped_column(String(80), nullable=True)

    batches: Mapped[list[Batch]] = relationship(back_populates="product")
    historical_complaints: Mapped[list[HistoricalComplaint]] = relationship(back_populates="product")


class ManufacturingLine(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "manufacturing_lines"
    __table_args__ = (
        UniqueConstraint("line_code", name="uq_manufacturing_lines_line_code"),
        Index("ix_manufacturing_lines_line_type", "line_type"),
        MYSQL_TABLE_KWARGS,
    )

    line_code: Mapped[str] = mapped_column(String(80), nullable=False)
    line_name: Mapped[str] = mapped_column(String(255), nullable=False)
    line_type: Mapped[str] = mapped_column(String(80), nullable=False)
    manufacturing_site: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)

    manufacturing_batches: Mapped[list[Batch]] = relationship(
        back_populates="manufacturing_line",
        foreign_keys="Batch.manufacturing_line_id",
    )
    packaging_batches: Mapped[list[Batch]] = relationship(
        back_populates="packaging_line",
        foreign_keys="Batch.packaging_line_id",
    )
    equipment_records: Mapped[list[Equipment]] = relationship(back_populates="manufacturing_line")
    deviations: Mapped[list[Deviation]] = relationship(back_populates="manufacturing_line")


class Supplier(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("supplier_code", name="uq_suppliers_supplier_code"),
        Index("ix_suppliers_supplier_name", "supplier_name"),
        MYSQL_TABLE_KWARGS,
    )

    supplier_code: Mapped[str] = mapped_column(String(80), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_type: Mapped[str] = mapped_column(String(80), nullable=False)
    qualification_status: Mapped[str] = mapped_column(String(80), nullable=False)
    country: Mapped[str | None] = mapped_column(String(150), nullable=True)

    material_lots: Mapped[list[MaterialLot]] = relationship(back_populates="supplier")
    packaging_material_lots: Mapped[list[PackagingMaterialLot]] = relationship(back_populates="supplier")


class Batch(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "batches"
    __table_args__ = (
        UniqueConstraint("batch_number", name="uq_batches_batch_number"),
        CheckConstraint("quantity_manufactured IS NULL OR quantity_manufactured >= 0", name="quantity_manufactured_non_negative"),
        CheckConstraint("quantity_released IS NULL OR quantity_released >= 0", name="quantity_released_non_negative"),
        Index("ix_batches_batch_number", "batch_number"),
        Index("ix_batches_status", "status"),
        MYSQL_TABLE_KWARGS,
    )

    batch_number: Mapped[str] = mapped_column(String(150), nullable=False)
    product_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    manufacturing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_retest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    manufacturing_line_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("manufacturing_lines.id", ondelete="SET NULL"),
        nullable=True,
    )
    packaging_line_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("manufacturing_lines.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity_manufactured: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    quantity_released: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)

    product: Mapped[Product] = relationship(back_populates="batches")
    manufacturing_line: Mapped[ManufacturingLine | None] = relationship(
        back_populates="manufacturing_batches",
        foreign_keys=[manufacturing_line_id],
    )
    packaging_line: Mapped[ManufacturingLine | None] = relationship(
        back_populates="packaging_batches",
        foreign_keys=[packaging_line_id],
    )
    material_lots: Mapped[list[MaterialLot]] = relationship(
        secondary=batch_material_lots,
        back_populates="batches",
    )
    packaging_material_lots: Mapped[list[PackagingMaterialLot]] = relationship(
        secondary=batch_packaging_material_lots,
        back_populates="batches",
    )
    equipment_records: Mapped[list[Equipment]] = relationship(
        secondary=batch_equipment,
        back_populates="batches",
    )
    deviations: Mapped[list[Deviation]] = relationship(back_populates="batch")
    historical_complaints: Mapped[list[HistoricalComplaint]] = relationship(back_populates="batch")
    distribution_records: Mapped[list[DistributionRecord]] = relationship(back_populates="batch")
    warehouse_inventory: Mapped[list[WarehouseInventory]] = relationship(back_populates="batch")


class MaterialLot(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "material_lots"
    __table_args__ = (
        UniqueConstraint("lot_number", name="uq_material_lots_lot_number"),
        Index("ix_material_lots_lot_number", "lot_number"),
        Index("ix_material_lots_material_code", "material_code"),
        MYSQL_TABLE_KWARGS,
    )

    material_code: Mapped[str] = mapped_column(String(80), nullable=False)
    material_name: Mapped[str] = mapped_column(String(255), nullable=False)
    lot_number: Mapped[str] = mapped_column(String(150), nullable=False)
    supplier_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    material_type: Mapped[str] = mapped_column(String(80), nullable=False)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_retest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(80), nullable=False)

    supplier: Mapped[Supplier | None] = relationship(back_populates="material_lots")
    batches: Mapped[list[Batch]] = relationship(
        secondary=batch_material_lots,
        back_populates="material_lots",
    )


class PackagingMaterialLot(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "packaging_material_lots"
    __table_args__ = (
        UniqueConstraint("lot_number", name="uq_packaging_material_lots_lot_number"),
        Index("ix_packaging_material_lots_lot_number", "lot_number"),
        Index("ix_packaging_material_lots_code", "packaging_material_code"),
        MYSQL_TABLE_KWARGS,
    )

    packaging_material_code: Mapped[str] = mapped_column(String(80), nullable=False)
    material_name: Mapped[str] = mapped_column(String(255), nullable=False)
    lot_number: Mapped[str] = mapped_column(String(150), nullable=False)
    supplier_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(80), nullable=False)

    supplier: Mapped[Supplier | None] = relationship(back_populates="packaging_material_lots")
    batches: Mapped[list[Batch]] = relationship(
        secondary=batch_packaging_material_lots,
        back_populates="packaging_material_lots",
    )


class Equipment(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "equipment"
    __table_args__ = (
        UniqueConstraint("equipment_code", name="uq_equipment_equipment_code"),
        MYSQL_TABLE_KWARGS,
    )

    equipment_code: Mapped[str] = mapped_column(String(80), nullable=False)
    equipment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    manufacturing_line_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("manufacturing_lines.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(80), nullable=False)

    manufacturing_line: Mapped[ManufacturingLine | None] = relationship(back_populates="equipment_records")
    batches: Mapped[list[Batch]] = relationship(
        secondary=batch_equipment,
        back_populates="equipment_records",
    )
    deviations: Mapped[list[Deviation]] = relationship(back_populates="equipment")


class Deviation(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "deviations"
    __table_args__ = (
        UniqueConstraint("deviation_number", name="uq_deviations_deviation_number"),
        Index("ix_deviations_status", "status"),
        Index("ix_deviations_severity", "severity"),
        MYSQL_TABLE_KWARGS,
    )

    deviation_number: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    batch_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    manufacturing_line_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("manufacturing_lines.id", ondelete="SET NULL"),
        nullable=True,
    )
    equipment_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("equipment.id", ondelete="SET NULL"),
        nullable=True,
    )
    opened_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)

    batch: Mapped[Batch | None] = relationship(back_populates="deviations")
    manufacturing_line: Mapped[ManufacturingLine | None] = relationship(back_populates="deviations")
    equipment: Mapped[Equipment | None] = relationship(back_populates="deviations")
    capas: Mapped[list[CAPA]] = relationship(back_populates="linked_deviation")


class CAPA(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "capas"
    __table_args__ = (
        UniqueConstraint("capa_number", name="uq_capas_capa_number"),
        Index("ix_capas_status", "status"),
        MYSQL_TABLE_KWARGS,
    )

    capa_number: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    linked_deviation_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("deviations.id", ondelete="SET NULL"),
        nullable=True,
    )
    effectiveness_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)

    linked_deviation: Mapped[Deviation | None] = relationship(back_populates="capas")


class DistributionRecord(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "distribution_records"
    __table_args__ = (
        Index("ix_distribution_records_batch_id", "batch_id"),
        Index("ix_distribution_records_market_city", "market_city"),
        CheckConstraint("quantity_distributed >= 0", name="quantity_distributed_non_negative"),
        MYSQL_TABLE_KWARGS,
    )

    batch_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    market_city: Mapped[str] = mapped_column(String(150), nullable=False)
    market_state: Mapped[str | None] = mapped_column(String(150), nullable=True)
    quantity_distributed: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    shipment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    shipment_status: Mapped[str] = mapped_column(String(80), nullable=False)

    batch: Mapped[Batch] = relationship(back_populates="distribution_records")


class WarehouseInventory(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "warehouse_inventory"
    __table_args__ = (
        UniqueConstraint("batch_id", "warehouse_name", name="uq_warehouse_inventory_batch_id_warehouse_name"),
        CheckConstraint("quantity_available >= 0", name="quantity_available_non_negative"),
        CheckConstraint("quantity_on_hold >= 0", name="quantity_on_hold_non_negative"),
        MYSQL_TABLE_KWARGS,
    )

    batch_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_name: Mapped[str] = mapped_column(String(180), nullable=False)
    quantity_available: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    quantity_on_hold: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    batch: Mapped[Batch] = relationship(back_populates="warehouse_inventory")


class HistoricalComplaint(UUIDPrimaryKeyMixin, TimestampMixin, DemoRecordMixin, Base):
    __tablename__ = "historical_complaints"
    __table_args__ = (
        UniqueConstraint("complaint_number", name="uq_historical_complaints_complaint_number"),
        Index("ix_historical_complaints_product_id", "product_id"),
        Index("ix_historical_complaints_batch_id", "batch_id"),
        Index("ix_historical_complaints_complaint_type", "complaint_type"),
        Index("ix_historical_complaints_severity", "severity"),
        Index("ix_historical_complaints_complaint_date", "complaint_date"),
        MYSQL_TABLE_KWARGS,
    )

    complaint_number: Mapped[str] = mapped_column(String(40), nullable=False)
    product_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    batch_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complaint_type: Mapped[str] = mapped_column(String(150), nullable=False)
    detailed_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    complaint_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    product: Mapped[Product | None] = relationship(back_populates="historical_complaints")
    batch: Mapped[Batch | None] = relationship(back_populates="historical_complaints")
