from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import PharmaQSentinelError
from app.models import (
    Batch,
    ComplaintDraft,
    Deviation,
    HistoricalComplaint,
    MaterialLot,
    PackagingMaterialLot,
    Product,
)
from app.repositories.batch_impact import BatchImpactRunRepository
from app.repositories.complaint_drafts import ComplaintDraftRepository
from app.repositories.reference import BatchRepository
from app.services.batch_impact.impact_score import overall_priority
from app.services.batch_impact.language_rules import (
    safe_connection_limitation,
    validate_payload_language,
)
from app.services.batch_impact.schemas import (
    BatchImpactEdge,
    BatchImpactNode,
    BatchImpactResponse,
    BatchImpactSummary,
    RecommendedAssessment,
)
from app.services.batch_impact.signal_engine import build_signals

ENGINE_PROVIDER = "deterministic"
ENGINE_MODEL = "batch-impact-rules-v1"


def decimal_text(value: Decimal | None) -> str:
    if value is None:
        return "0.000"
    return format(value, "f")


def graph_id(kind: str, record_id: str) -> str:
    return f"{kind}:{record_id}"


def _add_node(nodes: OrderedDict[str, BatchImpactNode], node: BatchImpactNode) -> None:
    nodes.setdefault(node.id, node)


def _add_edge(edges: OrderedDict[str, BatchImpactEdge], edge: BatchImpactEdge) -> None:
    edges.setdefault(edge.id, edge)


def _edge(
    edge_type: str,
    source: str,
    target: str,
    label: str,
    source_record_ids: list[str],
    why: str,
    confidence: str = "0.9000",
) -> BatchImpactEdge:
    return BatchImpactEdge(
        id=f"{edge_type}:{source}->{target}",
        source=source,
        target=target,
        type=edge_type,  # type: ignore[arg-type]
        relationship_label=label,
        source_record_ids=source_record_ids,
        why_connected=why,
        limitation=safe_connection_limitation(),
        confidence=confidence,
    )


def _safe_product_metadata(product: Product) -> dict[str, str | bool | None]:
    return {
        "product_code": product.product_code,
        "product_type": product.product_type,
        "strength_grade": product.strength_grade,
        "dosage_form": product.dosage_form,
        "demo_record": product.is_demo,
    }


def _safe_batch_metadata(batch: Batch) -> dict[str, str | bool | None]:
    return {
        "batch_number": batch.batch_number,
        "manufacturing_date": batch.manufacturing_date.isoformat() if batch.manufacturing_date else None,
        "expiry_retest_date": batch.expiry_retest_date.isoformat() if batch.expiry_retest_date else None,
        "quantity_released": decimal_text(batch.quantity_released),
        "demo_record": batch.is_demo,
    }


def _load_product_batches(db: Session, product_id: str) -> list[Batch]:
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
            selectinload(Batch.historical_complaints),
        )
        .where(Batch.product_id == product_id)
        .order_by(Batch.batch_number.asc())
    )
    return list(db.scalars(statement).unique().all())


def _load_historical_complaints(db: Session, product_id: str) -> list[HistoricalComplaint]:
    statement = (
        select(HistoricalComplaint)
        .options(selectinload(HistoricalComplaint.product), selectinload(HistoricalComplaint.batch))
        .where(HistoricalComplaint.product_id == product_id)
        .order_by(HistoricalComplaint.complaint_date.desc(), HistoricalComplaint.complaint_number.asc())
    )
    return list(db.scalars(statement).all())


def _similar_complaints(
    historical_complaints: list[HistoricalComplaint],
    draft: ComplaintDraft,
    primary_batch: Batch,
) -> list[HistoricalComplaint]:
    if not draft.complaint_type:
        return [
            complaint
            for complaint in historical_complaints
            if complaint.batch_id in {primary_batch.id, *(batch.id for batch in primary_batch.product.batches)}
        ]

    draft_type = draft.complaint_type.lower()
    return [
        complaint
        for complaint in historical_complaints
        if complaint.complaint_type.lower() == draft_type or draft_type in complaint.complaint_type.lower()
    ]


def build_batch_impact_analysis(
    db: Session,
    *,
    draft_id: str,
    created_by: str | None = None,
) -> BatchImpactResponse:
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    if not draft.batch_lot_number:
        raise PharmaQSentinelError("Draft must include a batch number before Batch Intelligence can run.", 409)

    primary_batch = BatchRepository(db).get_by_batch_number(draft.batch_lot_number)
    if primary_batch is None:
        raise PharmaQSentinelError(f"Batch not found in reference records: {draft.batch_lot_number}", 404)

    product_batches = _load_product_batches(db, primary_batch.product_id)
    historical_complaints = _load_historical_complaints(db, primary_batch.product_id)
    similar_complaints = _similar_complaints(historical_complaints, draft, primary_batch)

    nodes: OrderedDict[str, BatchImpactNode] = OrderedDict()
    edges: OrderedDict[str, BatchImpactEdge] = OrderedDict()
    complaint_node_id = graph_id("complaint", draft.id)
    product_node_id = graph_id("product", primary_batch.product.id)
    primary_batch_node_id = graph_id("batch", primary_batch.id)

    _add_node(
        nodes,
        BatchImpactNode(
            id=complaint_node_id,
            type="complaint",
            label="Current Draft Complaint",
            subtitle=draft.complaint_type or "Complaint type not provided",
            status=draft.status,
            severity=draft.suggested_severity,
            evidence_record_id=draft.id,
            metadata={
                "draft_id": draft.id,
                "batch_lot_number": draft.batch_lot_number,
                "demo_context": True,
            },
            position_hint="origin",
        ),
    )
    _add_node(
        nodes,
        BatchImpactNode(
            id=product_node_id,
            type="product",
            label=primary_batch.product.product_name,
            subtitle=primary_batch.product.product_code,
            status=primary_batch.product.market_status,
            evidence_record_id=primary_batch.product.id,
            metadata=_safe_product_metadata(primary_batch.product),
            position_hint="product",
        ),
    )
    _add_node(
        nodes,
        BatchImpactNode(
            id=primary_batch_node_id,
            type="batch",
            label=primary_batch.batch_number,
            subtitle="Complaint batch",
            status=primary_batch.status,
            evidence_record_id=primary_batch.id,
            metadata=_safe_batch_metadata(primary_batch),
            position_hint="primary",
        ),
    )
    _add_edge(
        edges,
        _edge(
            "COMPLAINT_INVOLVES",
            complaint_node_id,
            primary_batch_node_id,
            "Complaint involves batch",
            [draft.id, primary_batch.id],
            "The draft batch number matches this reference batch.",
        ),
    )
    _add_edge(
        edges,
        _edge(
            "PRODUCT_HAS_BATCH",
            product_node_id,
            primary_batch_node_id,
            "Product has batch",
            [primary_batch.product.id, primary_batch.id],
            "The reference batch is registered under this product.",
        ),
    )

    for batch in product_batches:
        batch_node_id = graph_id("batch", batch.id)
        _add_node(
            nodes,
            BatchImpactNode(
                id=batch_node_id,
                type="batch",
                label=batch.batch_number,
                subtitle="Related product batch" if batch.id != primary_batch.id else "Complaint batch",
                status=batch.status,
                evidence_record_id=batch.id,
                metadata=_safe_batch_metadata(batch),
                position_hint="related_batch" if batch.id != primary_batch.id else "primary",
            ),
        )
        _add_edge(
            edges,
            _edge(
                "PRODUCT_HAS_BATCH",
                product_node_id,
                batch_node_id,
                "Product has batch",
                [batch.product_id, batch.id],
                "This batch is registered under the same product record.",
            ),
        )

        for lot in batch.material_lots:
            lot_node_id = graph_id("material_lot", lot.id)
            _add_node(
                nodes,
                BatchImpactNode(
                    id=lot_node_id,
                    type="material_lot",
                    label=lot.lot_number,
                    subtitle=lot.material_name,
                    status=lot.status,
                    evidence_record_id=lot.id,
                    metadata={"material_code": lot.material_code, "material_type": lot.material_type},
                    position_hint="material",
                ),
            )
            _add_edge(
                edges,
                _edge(
                    "BATCH_USES_MATERIAL",
                    batch_node_id,
                    lot_node_id,
                    "Uses material lot",
                    [batch.id, lot.id],
                    "The batch manufacturing record links to this material lot.",
                ),
            )
            if lot.supplier:
                supplier_node_id = graph_id("supplier", lot.supplier.id)
                _add_node(
                    nodes,
                    BatchImpactNode(
                        id=supplier_node_id,
                        type="supplier",
                        label=lot.supplier.supplier_name,
                        subtitle=lot.supplier.supplier_code,
                        status=lot.supplier.qualification_status,
                        evidence_record_id=lot.supplier.id,
                        metadata={"supplier_type": lot.supplier.supplier_type, "country": lot.supplier.country},
                        position_hint="supplier",
                    ),
                )
                _add_edge(
                    edges,
                    _edge(
                        "MATERIAL_SUPPLIED_BY",
                        lot_node_id,
                        supplier_node_id,
                        "Material supplied by",
                        [lot.id, lot.supplier.id],
                        "The material lot references this supplier.",
                    ),
                )

        for lot in batch.packaging_material_lots:
            lot_node_id = graph_id("packaging_material_lot", lot.id)
            _add_node(
                nodes,
                BatchImpactNode(
                    id=lot_node_id,
                    type="packaging_material_lot",
                    label=lot.lot_number,
                    subtitle=lot.material_name,
                    status=lot.status,
                    evidence_record_id=lot.id,
                    metadata={"packaging_material_code": lot.packaging_material_code},
                    position_hint="packaging",
                ),
            )
            _add_edge(
                edges,
                _edge(
                    "BATCH_USES_PACKAGING",
                    batch_node_id,
                    lot_node_id,
                    "Uses packaging lot",
                    [batch.id, lot.id],
                    "The batch packaging record links to this packaging material lot.",
                ),
            )
            if lot.supplier:
                supplier_node_id = graph_id("supplier", lot.supplier.id)
                _add_node(
                    nodes,
                    BatchImpactNode(
                        id=supplier_node_id,
                        type="supplier",
                        label=lot.supplier.supplier_name,
                        subtitle=lot.supplier.supplier_code,
                        status=lot.supplier.qualification_status,
                        evidence_record_id=lot.supplier.id,
                        metadata={"supplier_type": lot.supplier.supplier_type, "country": lot.supplier.country},
                        position_hint="supplier",
                    ),
                )
                _add_edge(
                    edges,
                    _edge(
                        "PACKAGING_SUPPLIED_BY",
                        lot_node_id,
                        supplier_node_id,
                        "Packaging supplied by",
                        [lot.id, lot.supplier.id],
                        "The packaging material lot references this supplier.",
                    ),
                )

        if batch.manufacturing_line:
            line_node_id = graph_id("manufacturing_line", batch.manufacturing_line.id)
            _add_node(
                nodes,
                BatchImpactNode(
                    id=line_node_id,
                    type="manufacturing_line",
                    label=batch.manufacturing_line.line_code,
                    subtitle=batch.manufacturing_line.line_name,
                    status=batch.manufacturing_line.status,
                    evidence_record_id=batch.manufacturing_line.id,
                    metadata={"site": batch.manufacturing_line.manufacturing_site},
                    position_hint="line",
                ),
            )
            _add_edge(
                edges,
                _edge(
                    "BATCH_PROCESSED_ON",
                    batch_node_id,
                    line_node_id,
                    "Processed on line",
                    [batch.id, batch.manufacturing_line.id],
                    "The batch record references this manufacturing line.",
                ),
            )
        if batch.packaging_line:
            line_node_id = graph_id("packaging_line", batch.packaging_line.id)
            _add_node(
                nodes,
                BatchImpactNode(
                    id=line_node_id,
                    type="packaging_line",
                    label=batch.packaging_line.line_code,
                    subtitle=batch.packaging_line.line_name,
                    status=batch.packaging_line.status,
                    evidence_record_id=batch.packaging_line.id,
                    metadata={"site": batch.packaging_line.manufacturing_site},
                    position_hint="line",
                ),
            )
            _add_edge(
                edges,
                _edge(
                    "BATCH_PACKAGED_ON",
                    batch_node_id,
                    line_node_id,
                    "Packaged on line",
                    [batch.id, batch.packaging_line.id],
                    "The batch record references this packaging line.",
                ),
            )

        for equipment in batch.equipment_records:
            equipment_node_id = graph_id("equipment", equipment.id)
            _add_node(
                nodes,
                BatchImpactNode(
                    id=equipment_node_id,
                    type="equipment",
                    label=equipment.equipment_code,
                    subtitle=equipment.equipment_name,
                    status=equipment.status,
                    evidence_record_id=equipment.id,
                    metadata={"equipment_type": equipment.equipment_type},
                    position_hint="equipment",
                ),
            )
            _add_edge(
                edges,
                _edge(
                    "BATCH_USED_EQUIPMENT",
                    batch_node_id,
                    equipment_node_id,
                    "Used equipment",
                    [batch.id, equipment.id],
                    "The batch equipment history includes this equipment record.",
                ),
            )

        for deviation in batch.deviations:
            deviation_node_id = graph_id("deviation", deviation.id)
            _add_node(
                nodes,
                BatchImpactNode(
                    id=deviation_node_id,
                    type="deviation",
                    label=deviation.deviation_number,
                    subtitle=deviation.title,
                    status=deviation.status,
                    severity=deviation.severity,
                    evidence_record_id=deviation.id,
                    metadata={"opened_at": deviation.opened_at.isoformat() if deviation.opened_at else None},
                    position_hint="quality",
                ),
            )
            _add_edge(
                edges,
                _edge(
                    "BATCH_HAS_DEVIATION",
                    batch_node_id,
                    deviation_node_id,
                    "Has deviation",
                    [batch.id, deviation.id],
                    "The deviation record is linked to this batch.",
                ),
            )
            for capa in deviation.capas:
                capa_node_id = graph_id("capa", capa.id)
                _add_node(
                    nodes,
                    BatchImpactNode(
                        id=capa_node_id,
                        type="capa",
                        label=capa.capa_number,
                        subtitle=capa.title,
                        status=capa.status,
                        evidence_record_id=capa.id,
                        metadata={"effectiveness_status": capa.effectiveness_status},
                        position_hint="quality",
                    ),
                )
                _add_edge(
                    edges,
                    _edge(
                        "DEVIATION_LINKED_TO_CAPA",
                        deviation_node_id,
                        capa_node_id,
                        "Linked CAPA",
                        [deviation.id, capa.id],
                        "The CAPA record references this deviation.",
                    ),
                )

    for complaint in historical_complaints:
        if complaint.batch_id is None:
            continue
        complaint_node_id = graph_id("historical_complaint", complaint.id)
        _add_node(
            nodes,
            BatchImpactNode(
                id=complaint_node_id,
                type="historical_complaint",
                label=complaint.complaint_number,
                subtitle=complaint.complaint_type,
                status=complaint.status,
                severity=complaint.severity,
                evidence_record_id=complaint.id,
                metadata={"complaint_date": complaint.complaint_date.isoformat(), "demo_record": complaint.is_demo},
                position_hint="complaint_history",
            ),
        )
        batch_node_id = graph_id("batch", complaint.batch_id)
        _add_edge(
            edges,
            _edge(
                "BATCH_HAS_HISTORICAL_COMPLAINT",
                batch_node_id,
                complaint_node_id,
                "Historical complaint",
                [complaint.batch_id, complaint.id],
                "The historical complaint record is linked to this batch.",
            ),
        )
        if complaint in similar_complaints:
            _add_edge(
                edges,
                _edge(
                    "COMPLAINT_SIMILAR_TO",
                    graph_id("complaint", draft.id),
                    complaint_node_id,
                    "Similar complaint type",
                    [draft.id, complaint.id],
                    "The current draft and this historical complaint use a similar complaint type.",
                    confidence="0.7600",
                ),
            )

    for distribution in primary_batch.distribution_records:
        node_id = graph_id("distribution_location", distribution.id)
        _add_node(
            nodes,
            BatchImpactNode(
                id=node_id,
                type="distribution_location",
                label=distribution.market_city,
                subtitle=distribution.customer_name,
                status=distribution.shipment_status,
                evidence_record_id=distribution.id,
                metadata={
                    "market_state": distribution.market_state,
                    "quantity_distributed": decimal_text(distribution.quantity_distributed),
                    "shipment_date": distribution.shipment_date.isoformat() if distribution.shipment_date else None,
                    "demo_record": distribution.is_demo,
                },
                position_hint="distribution",
            ),
        )
        _add_edge(
            edges,
            _edge(
                "BATCH_DISTRIBUTED_TO",
                primary_batch_node_id,
                node_id,
                "Distributed to",
                [primary_batch.id, distribution.id],
                "Distribution history links the primary batch to this customer or market.",
            ),
        )

    for inventory in primary_batch.warehouse_inventory:
        node_id = graph_id("warehouse_inventory", inventory.id)
        _add_node(
            nodes,
            BatchImpactNode(
                id=node_id,
                type="warehouse_inventory",
                label=inventory.warehouse_name,
                subtitle=f"{decimal_text(inventory.quantity_available)} available",
                status="INTERNAL_INVENTORY",
                evidence_record_id=inventory.id,
                metadata={
                    "quantity_available": decimal_text(inventory.quantity_available),
                    "quantity_on_hold": decimal_text(inventory.quantity_on_hold),
                    "last_updated_at": inventory.last_updated_at.isoformat(),
                    "demo_record": inventory.is_demo,
                },
                position_hint="inventory",
            ),
        )
        _add_edge(
            edges,
            _edge(
                "BATCH_STORED_AT",
                primary_batch_node_id,
                node_id,
                "Stored at",
                [primary_batch.id, inventory.id],
                "Warehouse inventory record references the primary batch.",
            ),
        )

    primary_material_ids = {lot.id for lot in primary_batch.material_lots}
    primary_packaging_ids = {lot.id for lot in primary_batch.packaging_material_lots}
    primary_equipment_ids = {record.id for record in primary_batch.equipment_records}
    related_batches = [batch for batch in product_batches if batch.id != primary_batch.id]
    for batch in related_batches:
        related_node_id = graph_id("batch", batch.id)
        shared_material_ids = primary_material_ids.intersection(lot.id for lot in batch.material_lots)
        shared_packaging_ids = primary_packaging_ids.intersection(lot.id for lot in batch.packaging_material_lots)
        shared_equipment_ids = primary_equipment_ids.intersection(record.id for record in batch.equipment_records)
        if shared_material_ids:
            _add_edge(
                edges,
                _edge(
                    "BATCH_SHARES_MATERIAL_WITH",
                    primary_batch_node_id,
                    related_node_id,
                    "Shares material lot",
                    [primary_batch.id, batch.id, *sorted(shared_material_ids)],
                    "The primary and related batches reference one or more of the same material lots.",
                    confidence="0.8800",
                ),
            )
        if shared_packaging_ids:
            _add_edge(
                edges,
                _edge(
                    "BATCH_SHARES_PACKAGING_WITH",
                    primary_batch_node_id,
                    related_node_id,
                    "Shares packaging lot",
                    [primary_batch.id, batch.id, *sorted(shared_packaging_ids)],
                    "The primary and related batches reference one or more of the same packaging material lots.",
                    confidence="0.9000",
                ),
            )
        if shared_equipment_ids:
            _add_edge(
                edges,
                _edge(
                    "BATCH_SHARES_EQUIPMENT_WITH",
                    primary_batch_node_id,
                    related_node_id,
                    "Shares equipment",
                    [primary_batch.id, batch.id, *sorted(shared_equipment_ids)],
                    "The primary and related batches include one or more of the same equipment records.",
                    confidence="0.8000",
                ),
            )

    signals = build_signals(primary_batch=primary_batch, related_batches=related_batches, similar_complaints=similar_complaints)
    distributed_quantity = sum(
        (record.quantity_distributed for record in primary_batch.distribution_records),
        Decimal("0.000"),
    )
    remaining_inventory = sum(
        (record.quantity_available for record in primary_batch.warehouse_inventory),
        Decimal("0.000"),
    )
    open_deviations = [item for item in primary_batch.deviations if "OPEN" in item.status or "PROGRESS" in item.status]
    linked_capas = [capa for deviation in primary_batch.deviations for capa in deviation.capas]
    suppliers = sorted(
        {
            lot.supplier.supplier_name
            for lot in [*primary_batch.material_lots, *primary_batch.packaging_material_lots]
            if lot.supplier is not None
        }
    )
    limitations = [
        "Seeded reference data is fictional demonstration data and may not represent a complete company record.",
        "Relationships indicate records to assess; they do not prove causation or final quality impact.",
        "Distribution and inventory quantities are demo values that require authorised verification before action.",
    ]
    summary = BatchImpactSummary(
        primary_batch=primary_batch.batch_number,
        related_batches=[batch.batch_number for batch in related_batches],
        similar_complaint_count=len(similar_complaints),
        open_deviations=len(open_deviations),
        linked_capas=len(linked_capas),
        distributed_quantity=decimal_text(distributed_quantity),
        markets_or_locations=sorted({record.market_city for record in primary_batch.distribution_records}),
        remaining_inventory=decimal_text(remaining_inventory),
        suppliers_involved=suppliers,
        elevated_recurrence_signal=len(similar_complaints) >= 2,
        overall_investigation_priority=overall_priority(signals),
        data_limitations=limitations,
    )
    recommended_assessments = [
        RecommendedAssessment(
            title="Review primary batch retain samples",
            rationale="The complaint batch has related demo distribution, inventory, and complaint-history records to assess.",
            evidence_record_ids=[primary_batch.id],
            limitation=safe_connection_limitation(),
        ),
        RecommendedAssessment(
            title="Assess shared packaging lot records",
            rationale="Related batches share packaging material with the complaint batch in the demo records.",
            evidence_record_ids=[lot.id for lot in primary_batch.packaging_material_lots],
            limitation=safe_connection_limitation(),
        ),
        RecommendedAssessment(
            title="Review PL-04 deviation and CAPA status",
            rationale="An open packaging-line deviation and linked CAPA may be relevant to the complaint review.",
            evidence_record_ids=[item.id for item in open_deviations] + [item.id for item in linked_capas],
            limitation=safe_connection_limitation(),
        ),
    ]
    response = BatchImpactResponse(
        run_id="pending",
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        signals=signals,
        impact_summary=summary,
        recommended_assessments=recommended_assessments,
        limitations=limitations,
    )
    payload = response.model_dump(mode="json")
    validate_payload_language(payload)
    run = BatchImpactRunRepository(db).append(
        draft_id=draft.id,
        input_snapshot={
            "draft_id": draft.id,
            "batch_lot_number": draft.batch_lot_number,
            "product_name": draft.product_name,
            "complaint_type": draft.complaint_type,
        },
        graph_snapshot={"nodes": payload["nodes"], "edges": payload["edges"]},
        signals_json={"signals": payload["signals"]},
        summary_json=payload["impact_summary"],
        limitations_json={"limitations": payload["limitations"]},
        created_by=created_by or draft.created_by,
        provider=ENGINE_PROVIDER,
        model=ENGINE_MODEL,
        status="COMPLETE",
    )
    response.run_id = run.id
    return response
