from __future__ import annotations

from decimal import Decimal

from app.models import Batch, HistoricalComplaint
from app.services.batch_impact.language_rules import safe_connection_limitation
from app.services.batch_impact.schemas import BatchImpactSignal


def _confidence(value: str) -> str:
    return value


def build_signals(
    *,
    primary_batch: Batch,
    related_batches: list[Batch],
    similar_complaints: list[HistoricalComplaint],
) -> list[BatchImpactSignal]:
    signals: list[BatchImpactSignal] = []
    if len(similar_complaints) >= 2:
        signals.append(
            BatchImpactSignal(
                name="Repeated similar complaint pattern",
                category="complaint_history",
                level="ELEVATED",
                explanation=(
                    f"{len(similar_complaints)} historical demo complaints for the same product use a similar complaint type."
                ),
                evidence_record_ids=[complaint.id for complaint in similar_complaints],
                confidence=_confidence("0.7600"),
                recommended_assessment="Compare retained samples and complaint narratives across the similar complaint records.",
                limitation=safe_connection_limitation(),
            )
        )

    shared_packaging_batches = [
        batch
        for batch in related_batches
        if {lot.id for lot in batch.packaging_material_lots}.intersection(
            lot.id for lot in primary_batch.packaging_material_lots
        )
    ]
    if shared_packaging_batches:
        signals.append(
            BatchImpactSignal(
                name="Shared packaging material lot",
                category="materials",
                level="ELEVATED",
                explanation=(
                    f"{len(shared_packaging_batches)} related demo batches share packaging material lots with the complaint batch."
                ),
                evidence_record_ids=[lot.id for lot in primary_batch.packaging_material_lots],
                confidence=_confidence("0.9000"),
                recommended_assessment="Assess packaging material lot records and in-process packaging checks.",
                limitation=safe_connection_limitation(),
            )
        )

    shared_material_batches = [
        batch
        for batch in related_batches
        if {lot.id for lot in batch.material_lots}.intersection(lot.id for lot in primary_batch.material_lots)
    ]
    if shared_material_batches:
        signals.append(
            BatchImpactSignal(
                name="Shared API or raw material lot",
                category="materials",
                level="WATCH",
                explanation=(
                    f"{len(shared_material_batches)} related demo batches share API or raw material lots with the complaint batch."
                ),
                evidence_record_ids=[lot.id for lot in primary_batch.material_lots],
                confidence=_confidence("0.8600"),
                recommended_assessment="Review material release records and supplier lot documentation.",
                limitation=safe_connection_limitation(),
            )
        )

    shared_equipment_batches = [
        batch
        for batch in related_batches
        if {equipment.id for equipment in batch.equipment_records}.intersection(
            equipment.id for equipment in primary_batch.equipment_records
        )
    ]
    if shared_equipment_batches:
        signals.append(
            BatchImpactSignal(
                name="Shared processing or packaging equipment",
                category="equipment",
                level="WATCH",
                explanation=(
                    f"{len(shared_equipment_batches)} related demo batches share equipment records with the complaint batch."
                ),
                evidence_record_ids=[equipment.id for equipment in primary_batch.equipment_records],
                confidence=_confidence("0.8000"),
                recommended_assessment="Review equipment logs, line clearance, and process checks for the related batches.",
                limitation=safe_connection_limitation(),
            )
        )

    open_deviations = [
        deviation
        for deviation in primary_batch.deviations
        if "OPEN" in deviation.status or "PROGRESS" in deviation.status
    ]
    if open_deviations:
        signals.append(
            BatchImpactSignal(
                name="Open deviation on linked line or equipment",
                category="quality_event",
                level="HIGH",
                explanation="A linked open demo deviation may be relevant and should be investigated by QA.",
                evidence_record_ids=[deviation.id for deviation in open_deviations],
                confidence=_confidence("0.8800"),
                recommended_assessment="Review the deviation record, batch record timing, and any linked CAPA status.",
                limitation=safe_connection_limitation(),
            )
        )

    capas = [capa for deviation in primary_batch.deviations for capa in deviation.capas]
    pending_capas = [capa for capa in capas if capa.effectiveness_status and "PENDING" in capa.effectiveness_status]
    if pending_capas:
        signals.append(
            BatchImpactSignal(
                name="Linked CAPA effectiveness pending",
                category="quality_event",
                level="WATCH",
                explanation="A linked demo CAPA has pending effectiveness status and may need QA follow-up.",
                evidence_record_ids=[capa.id for capa in pending_capas],
                confidence=_confidence("0.8200"),
                recommended_assessment="Check whether CAPA actions or verification steps are relevant to this complaint review.",
                limitation=safe_connection_limitation(),
            )
        )

    remaining_inventory = sum(
        (record.quantity_available for record in primary_batch.warehouse_inventory),
        Decimal("0.000"),
    )
    if remaining_inventory > 0:
        signals.append(
            BatchImpactSignal(
                name="Remaining internal inventory",
                category="inventory",
                level="ELEVATED",
                explanation=f"Demo inventory records show {remaining_inventory:f} units available for assessment.",
                evidence_record_ids=[record.id for record in primary_batch.warehouse_inventory],
                confidence=_confidence("0.9200"),
                recommended_assessment="Confirm current inventory and assess whether retain or warehouse samples should be checked.",
                limitation=safe_connection_limitation(),
            )
        )

    markets = {record.market_city for record in primary_batch.distribution_records}
    if len(markets) >= 3:
        signals.append(
            BatchImpactSignal(
                name="Wide demo distribution",
                category="distribution",
                level="ELEVATED",
                explanation=f"Demo distribution records list {len(markets)} markets for the primary batch.",
                evidence_record_ids=[record.id for record in primary_batch.distribution_records],
                confidence=_confidence("0.9000"),
                recommended_assessment="Review market-level complaint intake and distribution quantities for assessment planning.",
                limitation=safe_connection_limitation(),
            )
        )

    supplier_ids = {
        lot.supplier_id
        for lot in [*primary_batch.material_lots, *primary_batch.packaging_material_lots]
        if lot.supplier_id is not None
    }
    if supplier_ids:
        signals.append(
            BatchImpactSignal(
                name="Supplier records involved",
                category="supplier",
                level="INFO",
                explanation="Supplier records are linked through material and packaging lot references.",
                evidence_record_ids=sorted(supplier_ids),
                confidence=_confidence("0.7800"),
                recommended_assessment="Review supplier lot certificates and any recent supplier quality signals.",
                limitation=safe_connection_limitation(),
            )
        )

    close_batches = [
        batch
        for batch in related_batches
        if batch.manufacturing_date
        and primary_batch.manufacturing_date
        and abs((batch.manufacturing_date - primary_batch.manufacturing_date).days) <= 7
    ]
    if close_batches:
        signals.append(
            BatchImpactSignal(
                name="Related batches in same manufacturing window",
                category="time_window",
                level="WATCH",
                explanation=(
                    f"{len(close_batches)} related demo batches were manufactured within seven days of the complaint batch."
                ),
                evidence_record_ids=[batch.id for batch in close_batches],
                confidence=_confidence("0.7400"),
                recommended_assessment="Compare batch manufacturing records, environmental context, and process checks for the window.",
                limitation=safe_connection_limitation(),
            )
        )

    return signals
