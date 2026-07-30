from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DecimalString, UTCDateTime


class ProductReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_code: str
    product_name: str
    product_type: str
    strength_grade: str | None = None
    dosage_form: str | None = None
    is_demo: bool


class ManufacturingLineReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    line_code: str
    line_name: str
    line_type: str
    manufacturing_site: str
    status: str
    is_demo: bool


class SupplierReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    supplier_code: str
    supplier_name: str
    supplier_type: str
    qualification_status: str
    country: str | None = None
    is_demo: bool


class MaterialLotReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    material_code: str
    material_name: str
    lot_number: str
    material_type: str
    received_date: date | None = None
    expiry_retest_date: date | None = None
    status: str
    supplier: SupplierReference | None = None
    is_demo: bool


class PackagingMaterialLotReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    packaging_material_code: str
    material_name: str
    lot_number: str
    received_date: date | None = None
    status: str
    supplier: SupplierReference | None = None
    is_demo: bool


class EquipmentReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    equipment_code: str
    equipment_name: str
    equipment_type: str
    status: str
    is_demo: bool


class CAPAReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    capa_number: str
    title: str
    description: str | None = None
    status: str
    effectiveness_status: str | None = None
    opened_at: UTCDateTime | None = None
    target_date: date | None = None
    closed_at: UTCDateTime | None = None
    is_demo: bool


class DeviationReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    deviation_number: str
    title: str
    description: str | None = None
    status: str
    severity: str
    opened_at: UTCDateTime | None = None
    closed_at: UTCDateTime | None = None
    capas: list[CAPAReference] = Field(default_factory=list)
    is_demo: bool


class DistributionRecordReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_name: str
    market_city: str
    market_state: str | None = None
    quantity_distributed: DecimalString
    shipment_date: date | None = None
    shipment_status: str
    is_demo: bool


class DistributionSummary(BaseModel):
    total_quantity_distributed: DecimalString
    records: list[DistributionRecordReference]


class WarehouseInventoryReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    warehouse_name: str
    quantity_available: DecimalString
    quantity_on_hold: DecimalString
    last_updated_at: UTCDateTime
    is_demo: bool


class BatchReferenceResponse(BaseModel):
    id: str
    batch_number: str
    manufacturing_date: date | None = None
    expiry_retest_date: date | None = None
    status: str
    quantity_manufactured: DecimalString | None = None
    quantity_released: DecimalString | None = None
    is_demo: bool
    product: ProductReferenceResponse
    manufacturing_line: ManufacturingLineReference | None = None
    packaging_line: ManufacturingLineReference | None = None
    material_lots: list[MaterialLotReference]
    packaging_material_lots: list[PackagingMaterialLotReference]
    equipment: list[EquipmentReference]
    deviations: list[DeviationReference]
    distribution_summary: DistributionSummary
    warehouse_inventory: list[WarehouseInventoryReference]


class SeedStatusResponse(BaseModel):
    products: int
    batches: int
    suppliers: int
    materials: int
    packaging_materials: int
    equipment: int
    deviations: int
    capas: int
    historical_complaints: int
    distribution_records: int
    warehouse_inventory: int


class HistoricalComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_number: str
    product_id: str | None = None
    batch_id: str | None = None
    product_name: str | None = None
    batch_number: str | None = None
    customer_name: str | None = None
    complaint_type: str
    detailed_description: str
    severity: str
    complaint_date: date
    status: str
    is_demo: bool
