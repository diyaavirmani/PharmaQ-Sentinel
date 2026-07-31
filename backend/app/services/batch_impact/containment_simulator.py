from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import PharmaQSentinelError
from app.models import Batch
from app.repositories.complaint_drafts import ComplaintDraftRepository
from app.repositories.reference import BatchRepository
from app.services.batch_impact.graph_builder import _load_product_batches, decimal_text
from app.services.batch_impact.language_rules import (
    safe_simulation_limitation,
    validate_payload_language,
)
from app.services.batch_impact.schemas import (
    ContainmentBatchScope,
    ContainmentSimulationRequest,
    ContainmentSimulationResponse,
)


def _append_reason(reasons_by_batch: dict[str, list[str]], batch: Batch, reason: str) -> None:
    reasons_by_batch.setdefault(batch.id, [])
    if reason not in reasons_by_batch[batch.id]:
        reasons_by_batch[batch.id].append(reason)


def simulate_containment_scope(
    db: Session,
    *,
    draft_id: str,
    request: ContainmentSimulationRequest,
) -> ContainmentSimulationResponse:
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    if not draft.batch_lot_number:
        raise PharmaQSentinelError("Draft must include a batch number before containment simulation can run.", 409)

    primary_batch = BatchRepository(db).get_by_batch_number(draft.batch_lot_number)
    if primary_batch is None:
        raise PharmaQSentinelError(f"Batch not found in reference records: {draft.batch_lot_number}", 404)

    product_batches = _load_product_batches(db, primary_batch.product_id)
    reasons_by_batch: dict[str, list[str]] = {}
    if request.include_primary_batch:
        _append_reason(reasons_by_batch, primary_batch, "Primary complaint batch selected.")

    primary_packaging_ids = {lot.id for lot in primary_batch.packaging_material_lots}
    primary_material_ids = {lot.id for lot in primary_batch.material_lots}
    primary_equipment_ids = {equipment.id for equipment in primary_batch.equipment_records}
    for batch in product_batches:
        if batch.id == primary_batch.id:
            continue
        if request.include_shared_packaging_lot and primary_packaging_ids.intersection(
            lot.id for lot in batch.packaging_material_lots
        ):
            _append_reason(reasons_by_batch, batch, "Shares packaging material lot with the complaint batch.")
        if request.include_shared_material_lot and primary_material_ids.intersection(lot.id for lot in batch.material_lots):
            _append_reason(reasons_by_batch, batch, "Shares API or raw material lot with the complaint batch.")
        if request.include_shared_equipment and primary_equipment_ids.intersection(
            equipment.id for equipment in batch.equipment_records
        ):
            if primary_batch.manufacturing_date and batch.manufacturing_date:
                delta = abs((batch.manufacturing_date - primary_batch.manufacturing_date).days)
                if delta <= request.equipment_date_window_days:
                    _append_reason(
                        reasons_by_batch,
                        batch,
                        f"Shares equipment within {request.equipment_date_window_days} days of the complaint batch.",
                    )
            else:
                _append_reason(reasons_by_batch, batch, "Shares equipment with the complaint batch.")

    included_batches = [batch for batch in product_batches if batch.id in reasons_by_batch]
    included_batches.sort(key=lambda item: item.batch_number)
    distributed_quantity = sum(
        (
            distribution.quantity_distributed
            for batch in included_batches
            for distribution in batch.distribution_records
        ),
        Decimal("0.000"),
    )
    internal_inventory = sum(
        (inventory.quantity_available for batch in included_batches for inventory in batch.warehouse_inventory),
        Decimal("0.000"),
    )
    markets = sorted(
        {
            f"{record.customer_name} - {record.market_city}"
            for batch in included_batches
            for record in batch.distribution_records
        }
    )
    open_shipments = sorted(
        {
            f"{record.customer_name} - {record.market_city}"
            for batch in included_batches
            for record in batch.distribution_records
            if "OPEN" in record.shipment_status
        }
    )
    response = ContainmentSimulationResponse(
        batches_included=[
            ContainmentBatchScope(
                batch_number=batch.batch_number,
                product_name=batch.product.product_name,
                inclusion_reasons=reasons_by_batch[batch.id],
            )
            for batch in included_batches
        ],
        internal_inventory_potentially_assessed=decimal_text(internal_inventory),
        distributed_quantity=decimal_text(distributed_quantity),
        customers_or_markets_requiring_assessment=markets,
        open_shipments=open_shipments,
        recommended_sample_checks=[
            "Inspect retained samples for the primary complaint batch.",
            "Review blister integrity and appearance checks for batches included in this simulated scope.",
            "Compare complaint narratives and retain observations before deciding any operational action.",
        ],
        possible_supply_impact=(
            "Scope may include assessment of available warehouse inventory and distributed demo markets for included batches."
        ),
        limitations=[
            safe_simulation_limitation(),
            "The scope is based on available seeded reference records only.",
            "A qualified reviewer must decide any actual containment, hold, recall, or communication action.",
        ],
        simulation_only=True,
    )
    validate_payload_language(response.model_dump(mode="json"))
    return response
