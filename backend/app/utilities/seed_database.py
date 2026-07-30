from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    CAPA,
    Batch,
    Deviation,
    DistributionRecord,
    Equipment,
    HistoricalComplaint,
    ManufacturingLine,
    MaterialLot,
    PackagingMaterialLot,
    Product,
    ProductType,
    RecordSource,
    Severity,
    Supplier,
    WarehouseInventory,
)
from app.repositories.reference import ReferenceCountRepository

ModelT = TypeVar("ModelT")

DEMO_SOURCE = RecordSource.MANUAL_DEMO_SEED.value


def utc_datetime(year: int, month: int, day: int, hour: int = 9) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=UTC)


def get_or_create(
    db: Session,
    model: type[ModelT],
    lookup: dict[str, Any],
    defaults: dict[str, Any],
) -> ModelT:
    statement = select(model).filter_by(**lookup)
    instance = db.scalars(statement).first()
    values = {**defaults, "is_demo": True, "record_source": DEMO_SOURCE}
    if instance is None:
        instance = model(**lookup, **values)
        db.add(instance)
        db.flush()
        return instance

    for key, value in values.items():
        setattr(instance, key, value)
    db.flush()
    return instance


def link_once(collection: list[ModelT], item: ModelT) -> None:
    item_id = item.id
    if all(existing.id != item_id for existing in collection):
        collection.append(item)


def seed_products(db: Session) -> dict[str, Product]:
    rows = [
        (
            "AMOX-CAP-500",
            {
                "product_name": "Amoxicillin Capsules 500 mg",
                "product_type": ProductType.FDF.value,
                "strength_grade": "500 mg",
                "dosage_form": "Capsule",
                "market_status": "DEMONSTRATION_ACTIVE",
            },
        ),
        (
            "AMOX-API",
            {
                "product_name": "Amoxicillin API",
                "product_type": ProductType.API.value,
                "strength_grade": "Compendial API grade",
                "dosage_form": None,
                "market_status": "DEMONSTRATION_ACTIVE",
            },
        ),
        (
            "PARA-TAB-500",
            {
                "product_name": "Paracetamol Tablets 500 mg",
                "product_type": ProductType.FDF.value,
                "strength_grade": "500 mg",
                "dosage_form": "Tablet",
                "market_status": "DEMONSTRATION_ACTIVE",
            },
        ),
        (
            "CEF-INJ-1G",
            {
                "product_name": "Ceftriaxone Injection",
                "product_type": ProductType.FDF.value,
                "strength_grade": "1 g",
                "dosage_form": "Injection",
                "market_status": "DEMONSTRATION_ACTIVE",
            },
        ),
        (
            "OME-CAP-20",
            {
                "product_name": "Omeprazole Capsules 20 mg",
                "product_type": ProductType.FDF.value,
                "strength_grade": "20 mg",
                "dosage_form": "Capsule",
                "market_status": "DEMONSTRATION_ACTIVE",
            },
        ),
    ]
    return {
        code: get_or_create(db, Product, {"product_code": code}, defaults)
        for code, defaults in rows
    }


def seed_lines(db: Session) -> dict[str, ManufacturingLine]:
    return {
        "ML-02": get_or_create(
            db,
            ManufacturingLine,
            {"line_code": "ML-02"},
            {
                "line_name": "Oral Solid Manufacturing Line 02",
                "line_type": "MANUFACTURING",
                "manufacturing_site": "Demo Formulation Site A",
                "status": "QUALIFIED",
            },
        ),
        "PL-04": get_or_create(
            db,
            ManufacturingLine,
            {"line_code": "PL-04"},
            {
                "line_name": "Packaging Line PL-04",
                "line_type": "PACKAGING",
                "manufacturing_site": "Demo Formulation Site A",
                "status": "QUALIFIED",
            },
        ),
    }


def seed_suppliers(db: Session) -> dict[str, Supplier]:
    return {
        "SUP-API-001": get_or_create(
            db,
            Supplier,
            {"supplier_code": "SUP-API-001"},
            {
                "supplier_name": "Demo API Supply Co.",
                "supplier_type": "API",
                "qualification_status": "QUALIFIED_DEMO",
                "country": "India",
            },
        ),
        "SUP-PKG-001": get_or_create(
            db,
            Supplier,
            {"supplier_code": "SUP-PKG-001"},
            {
                "supplier_name": "Demo Pack Materials Pvt. Ltd.",
                "supplier_type": "PACKAGING_MATERIAL",
                "qualification_status": "QUALIFIED_DEMO",
                "country": "India",
            },
        ),
    }


def seed_lots(db: Session, suppliers: dict[str, Supplier]) -> tuple[dict[str, MaterialLot], dict[str, PackagingMaterialLot]]:
    material_lots = {
        "AMX-API-L2405": get_or_create(
            db,
            MaterialLot,
            {"lot_number": "AMX-API-L2405"},
            {
                "material_code": "AMX-API",
                "material_name": "Amoxicillin API",
                "supplier_id": suppliers["SUP-API-001"].id,
                "material_type": "API",
                "received_date": date(2024, 5, 15),
                "expiry_retest_date": date(2026, 5, 15),
                "status": "RELEASED",
            },
        ),
        "MCC-L2406": get_or_create(
            db,
            MaterialLot,
            {"lot_number": "MCC-L2406"},
            {
                "material_code": "MCC-101",
                "material_name": "Microcrystalline Cellulose",
                "supplier_id": suppliers["SUP-API-001"].id,
                "material_type": "EXCIPIENT",
                "received_date": date(2024, 6, 1),
                "expiry_retest_date": date(2027, 6, 1),
                "status": "RELEASED",
            },
        ),
    }

    packaging_lots = {
        "ALU-BLISTER-L2406": get_or_create(
            db,
            PackagingMaterialLot,
            {"lot_number": "ALU-BLISTER-L2406"},
            {
                "packaging_material_code": "ALU-PVC-250",
                "material_name": "Alu-PVC Blister Foil",
                "supplier_id": suppliers["SUP-PKG-001"].id,
                "received_date": date(2024, 6, 5),
                "status": "RELEASED",
            },
        )
    }
    return material_lots, packaging_lots


def seed_equipment(db: Session, lines: dict[str, ManufacturingLine]) -> dict[str, Equipment]:
    rows = [
        (
            "EQ-PL04-SEALER",
            {
                "equipment_name": "PL-04 Blister Sealer",
                "equipment_type": "BLISTER_SEALER",
                "manufacturing_line_id": lines["PL-04"].id,
                "status": "QUALIFIED",
            },
        ),
        (
            "EQ-PL04-CAMERA",
            {
                "equipment_name": "PL-04 Vision Inspection Camera",
                "equipment_type": "VISION_INSPECTION",
                "manufacturing_line_id": lines["PL-04"].id,
                "status": "QUALIFIED",
            },
        ),
        (
            "EQ-ML02-BLENDER",
            {
                "equipment_name": "ML-02 Powder Blender",
                "equipment_type": "BLENDER",
                "manufacturing_line_id": lines["ML-02"].id,
                "status": "QUALIFIED",
            },
        ),
    ]
    return {
        code: get_or_create(db, Equipment, {"equipment_code": code}, defaults)
        for code, defaults in rows
    }


def seed_batches(
    db: Session,
    products: dict[str, Product],
    lines: dict[str, ManufacturingLine],
    material_lots: dict[str, MaterialLot],
    packaging_lots: dict[str, PackagingMaterialLot],
    equipment: dict[str, Equipment],
) -> dict[str, Batch]:
    batch_defaults = {
        "product_id": products["AMOX-CAP-500"].id,
        "manufacturing_line_id": lines["ML-02"].id,
        "packaging_line_id": lines["PL-04"].id,
        "status": "RELEASED_DEMO",
    }
    rows = [
        ("BMX240602", date(2024, 6, 2), date(2026, 6, 1), Decimal("125000.000"), Decimal("123900.000")),
        ("BMX240603", date(2024, 6, 3), date(2026, 6, 2), Decimal("128000.000"), Decimal("127100.000")),
        ("BMX240604", date(2024, 6, 4), date(2026, 6, 3), Decimal("130000.000"), Decimal("129250.000")),
    ]
    batches = {
        number: get_or_create(
            db,
            Batch,
            {"batch_number": number},
            {
                **batch_defaults,
                "manufacturing_date": manufacturing_date,
                "expiry_retest_date": expiry_retest_date,
                "quantity_manufactured": quantity_manufactured,
                "quantity_released": quantity_released,
            },
        )
        for number, manufacturing_date, expiry_retest_date, quantity_manufactured, quantity_released in rows
    }

    for batch in batches.values():
        for material_lot in material_lots.values():
            link_once(batch.material_lots, material_lot)
        for packaging_lot in packaging_lots.values():
            link_once(batch.packaging_material_lots, packaging_lot)
        for equipment_record in equipment.values():
            link_once(batch.equipment_records, equipment_record)
    db.flush()
    return batches


def seed_quality_records(
    db: Session,
    batches: dict[str, Batch],
    lines: dict[str, ManufacturingLine],
    equipment: dict[str, Equipment],
) -> None:
    deviation = get_or_create(
        db,
        Deviation,
        {"deviation_number": "DEV-2026-023"},
        {
            "title": "Seal temperature excursion observed on PL-04",
            "description": (
                "Fictional demonstration deviation involving intermittent lower seal "
                "temperature alarms on packaging line PL-04 during blister sealing."
            ),
            "status": "OPEN_DEMO",
            "severity": Severity.MAJOR.value,
            "batch_id": batches["BMX240602"].id,
            "manufacturing_line_id": lines["PL-04"].id,
            "equipment_id": equipment["EQ-PL04-SEALER"].id,
            "opened_at": utc_datetime(2026, 7, 12, 10),
            "closed_at": None,
        },
    )
    get_or_create(
        db,
        CAPA,
        {"capa_number": "CAPA-2026-014"},
        {
            "title": "Review PL-04 seal-temperature controls",
            "description": (
                "Fictional demonstration CAPA to verify heater block calibration, "
                "operator response checks, and in-process blister seal sampling."
            ),
            "status": "IN_PROGRESS_DEMO",
            "linked_deviation_id": deviation.id,
            "effectiveness_status": "PENDING_DEMO",
            "opened_at": utc_datetime(2026, 7, 15, 9),
            "target_date": date(2026, 8, 15),
            "closed_at": None,
        },
    )


def seed_distribution_and_inventory(db: Session, batch: Batch) -> None:
    distribution_rows = [
        ("Delhi Demo Hospital", "Delhi", "Delhi", Decimal("18000.000"), date(2024, 6, 20), "SHIPPED_DEMO"),
        ("Mumbai Demo Distributor", "Mumbai", "Maharashtra", Decimal("22000.000"), date(2024, 6, 22), "SHIPPED_DEMO"),
        ("Jaipur Demo Pharmacy", "Jaipur", "Rajasthan", Decimal("9500.000"), date(2024, 6, 24), "SHIPPED_DEMO"),
    ]
    for customer_name, city, state, quantity, shipment_date, status in distribution_rows:
        get_or_create(
            db,
            DistributionRecord,
            {"batch_id": batch.id, "customer_name": customer_name, "market_city": city},
            {
                "market_state": state,
                "quantity_distributed": quantity,
                "shipment_date": shipment_date,
                "shipment_status": status,
            },
        )

    get_or_create(
        db,
        WarehouseInventory,
        {"batch_id": batch.id, "warehouse_name": "Central Demo Warehouse"},
        {
            "quantity_available": Decimal("51000.000"),
            "quantity_on_hold": Decimal("2500.000"),
            "last_updated_at": utc_datetime(2026, 7, 30, 8),
        },
    )


def historical_rows(products: dict[str, Product], batches: dict[str, Batch]) -> Iterable[tuple[str, dict[str, Any]]]:
    amox = products["AMOX-CAP-500"]
    api = products["AMOX-API"]
    para = products["PARA-TAB-500"]
    cef = products["CEF-INJ-1G"]
    ome = products["OME-CAP-20"]

    return [
        (
            "HC-DEMO-2026-001",
            {
                "product_id": amox.id,
                "batch_id": batches["BMX240602"].id,
                "customer_name": "Delhi Demo Hospital",
                "complaint_type": "capsule discolouration",
                "detailed_description": "Fictional demo complaint: capsules appeared pale yellow-brown.",
                "severity": Severity.MAJOR.value,
                "complaint_date": date(2026, 7, 20),
                "status": "CLOSED_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-002",
            {
                "product_id": amox.id,
                "batch_id": batches["BMX240603"].id,
                "customer_name": "Mumbai Demo Distributor",
                "complaint_type": "capsule discolouration",
                "detailed_description": "Fictional demo complaint: isolated strip with capsule colour variation.",
                "severity": Severity.MINOR.value,
                "complaint_date": date(2026, 7, 22),
                "status": "UNDER_REVIEW_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-003",
            {
                "product_id": amox.id,
                "batch_id": batches["BMX240604"].id,
                "customer_name": "Jaipur Demo Pharmacy",
                "complaint_type": "capsule discolouration",
                "detailed_description": "Fictional demo complaint: customer noted darker capsules in one blister.",
                "severity": Severity.MINOR.value,
                "complaint_date": date(2026, 7, 24),
                "status": "OPEN_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-004",
            {
                "product_id": para.id,
                "batch_id": None,
                "customer_name": "Demo Clinic A",
                "complaint_type": "broken tablets",
                "detailed_description": "Fictional demo complaint: tablets broken inside bottle.",
                "severity": Severity.MINOR.value,
                "complaint_date": date(2026, 6, 10),
                "status": "CLOSED_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-005",
            {
                "product_id": para.id,
                "batch_id": None,
                "customer_name": "Demo Clinic B",
                "complaint_type": "missing tablets",
                "detailed_description": "Fictional demo complaint: count short by two tablets.",
                "severity": Severity.MINOR.value,
                "complaint_date": date(2026, 6, 11),
                "status": "CLOSED_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-006",
            {
                "product_id": amox.id,
                "batch_id": batches["BMX240602"].id,
                "customer_name": "Demo Distributor West",
                "complaint_type": "blister leakage",
                "detailed_description": "Fictional demo complaint: suspected blister pocket leakage.",
                "severity": Severity.MAJOR.value,
                "complaint_date": date(2026, 7, 25),
                "status": "OPEN_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-007",
            {
                "product_id": ome.id,
                "batch_id": None,
                "customer_name": "Demo Pharmacy North",
                "complaint_type": "wrong label",
                "detailed_description": "Fictional demo complaint: carton label did not match bottle label.",
                "severity": Severity.MAJOR.value,
                "complaint_date": date(2026, 5, 18),
                "status": "CLOSED_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-008",
            {
                "product_id": cef.id,
                "batch_id": None,
                "customer_name": "Demo Hospital East",
                "complaint_type": "foreign particles",
                "detailed_description": "Fictional demo complaint: visible particle reported before use.",
                "severity": Severity.CRITICAL.value,
                "complaint_date": date(2026, 5, 20),
                "status": "CLOSED_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-009",
            {
                "product_id": api.id,
                "batch_id": None,
                "customer_name": "Demo API Customer",
                "complaint_type": "API assay discrepancy",
                "detailed_description": "Fictional demo complaint: customer assay result below expected range.",
                "severity": Severity.MAJOR.value,
                "complaint_date": date(2026, 4, 8),
                "status": "CLOSED_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-010",
            {
                "product_id": api.id,
                "batch_id": None,
                "customer_name": "Demo API Customer",
                "complaint_type": "API moisture discrepancy",
                "detailed_description": "Fictional demo complaint: moisture result above internal alert trend.",
                "severity": Severity.MAJOR.value,
                "complaint_date": date(2026, 4, 14),
                "status": "CLOSED_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-011",
            {
                "product_id": cef.id,
                "batch_id": None,
                "customer_name": "Demo Hospital South",
                "complaint_type": "damaged container",
                "detailed_description": "Fictional demo complaint: vial container crack observed on receipt.",
                "severity": Severity.MAJOR.value,
                "complaint_date": date(2026, 3, 12),
                "status": "CLOSED_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-012",
            {
                "product_id": para.id,
                "batch_id": None,
                "customer_name": "Demo Patient Report",
                "complaint_type": "suspected adverse event",
                "detailed_description": "Fictional demo complaint: consumer reported symptoms after ingestion.",
                "severity": Severity.CRITICAL.value,
                "complaint_date": date(2026, 3, 21),
                "status": "REFERRED_DEMO",
            },
        ),
        (
            "HC-DEMO-2026-013",
            {
                "product_id": ome.id,
                "batch_id": None,
                "customer_name": "Demo Pharmacy Central",
                "complaint_type": "suspected counterfeit or tampering",
                "detailed_description": "Fictional demo complaint: tamper band appeared previously opened.",
                "severity": Severity.CRITICAL.value,
                "complaint_date": date(2026, 2, 28),
                "status": "REFERRED_DEMO",
            },
        ),
    ]


def seed_historical_complaints(
    db: Session,
    products: dict[str, Product],
    batches: dict[str, Batch],
) -> None:
    for complaint_number, defaults in historical_rows(products, batches):
        get_or_create(
            db,
            HistoricalComplaint,
            {"complaint_number": complaint_number},
            {
                **defaults,
                "metadata_json": {
                    "demo": True,
                    "source": DEMO_SOURCE,
                    "notice": "Fictional demonstration record; not a real company complaint.",
                },
            },
        )


def seed_database(db: Session) -> dict[str, int]:
    products = seed_products(db)
    lines = seed_lines(db)
    suppliers = seed_suppliers(db)
    material_lots, packaging_lots = seed_lots(db, suppliers)
    equipment = seed_equipment(db, lines)
    batches = seed_batches(db, products, lines, material_lots, packaging_lots, equipment)
    seed_quality_records(db, batches, lines, equipment)
    seed_distribution_and_inventory(db, batches["BMX240602"])
    seed_historical_complaints(db, products, batches)
    db.flush()
    return ReferenceCountRepository(db).seed_status_counts()


def main() -> None:
    with SessionLocal() as db:
        counts = seed_database(db)
        db.commit()
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
