from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime

NodeType = Literal[
    "complaint",
    "product",
    "batch",
    "material_lot",
    "packaging_material_lot",
    "supplier",
    "manufacturing_line",
    "packaging_line",
    "equipment",
    "deviation",
    "capa",
    "historical_complaint",
    "distribution_location",
    "warehouse_inventory",
]

EdgeType = Literal[
    "COMPLAINT_INVOLVES",
    "PRODUCT_HAS_BATCH",
    "BATCH_USES_MATERIAL",
    "BATCH_USES_PACKAGING",
    "MATERIAL_SUPPLIED_BY",
    "PACKAGING_SUPPLIED_BY",
    "BATCH_PROCESSED_ON",
    "BATCH_PACKAGED_ON",
    "BATCH_USED_EQUIPMENT",
    "BATCH_HAS_DEVIATION",
    "DEVIATION_LINKED_TO_CAPA",
    "BATCH_HAS_HISTORICAL_COMPLAINT",
    "BATCH_DISTRIBUTED_TO",
    "BATCH_STORED_AT",
    "BATCH_SHARES_MATERIAL_WITH",
    "BATCH_SHARES_PACKAGING_WITH",
    "BATCH_SHARES_EQUIPMENT_WITH",
    "COMPLAINT_SIMILAR_TO",
]


class BatchImpactRunRequest(BaseModel):
    created_by: str | None = Field(default="Demo User", max_length=150)


class BatchImpactNode(BaseModel):
    id: str
    type: NodeType
    label: str
    subtitle: str | None = None
    status: str | None = None
    severity: str | None = None
    evidence_record_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    position_hint: str | None = None


class BatchImpactEdge(BaseModel):
    id: str
    source: str
    target: str
    type: EdgeType
    relationship_label: str
    source_record_ids: list[str] = Field(default_factory=list)
    why_connected: str
    limitation: str
    confidence: str | None = None


class BatchImpactSignal(BaseModel):
    name: str
    category: str
    level: Literal["INFO", "WATCH", "ELEVATED", "HIGH"]
    explanation: str
    evidence_record_ids: list[str] = Field(default_factory=list)
    confidence: str
    recommended_assessment: str
    limitation: str


class BatchImpactSummary(BaseModel):
    primary_batch: str
    related_batches: list[str]
    similar_complaint_count: int
    open_deviations: int
    linked_capas: int
    distributed_quantity: str
    markets_or_locations: list[str]
    remaining_inventory: str
    suppliers_involved: list[str]
    elevated_recurrence_signal: bool
    overall_investigation_priority: str
    data_limitations: list[str]


class RecommendedAssessment(BaseModel):
    title: str
    rationale: str
    evidence_record_ids: list[str] = Field(default_factory=list)
    limitation: str


class BatchImpactResponse(BaseModel):
    run_id: str
    nodes: list[BatchImpactNode]
    edges: list[BatchImpactEdge]
    signals: list[BatchImpactSignal]
    impact_summary: BatchImpactSummary
    recommended_assessments: list[RecommendedAssessment]
    limitations: list[str]


class ContainmentSimulationRequest(BaseModel):
    include_primary_batch: bool = True
    include_shared_packaging_lot: bool = True
    include_shared_material_lot: bool = False
    include_shared_equipment: bool = False
    equipment_date_window_days: int = Field(default=7, ge=0, le=90)


class ContainmentBatchScope(BaseModel):
    batch_number: str
    product_name: str
    inclusion_reasons: list[str]


class ContainmentSimulationResponse(BaseModel):
    batches_included: list[ContainmentBatchScope]
    internal_inventory_potentially_assessed: str
    distributed_quantity: str
    customers_or_markets_requiring_assessment: list[str]
    open_shipments: list[str]
    recommended_sample_checks: list[str]
    possible_supply_impact: str
    limitations: list[str]
    simulation_only: bool = True


class BatchImpactRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str
    created_at: UTCDateTime
    created_by: str | None = None
    provider: str | None = None
    model: str | None = None
    status: str
