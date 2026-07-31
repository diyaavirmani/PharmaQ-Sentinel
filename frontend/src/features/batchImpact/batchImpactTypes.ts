export type BatchImpactNodeType =
  | "complaint"
  | "product"
  | "batch"
  | "material_lot"
  | "packaging_material_lot"
  | "supplier"
  | "manufacturing_line"
  | "packaging_line"
  | "equipment"
  | "deviation"
  | "capa"
  | "historical_complaint"
  | "distribution_location"
  | "warehouse_inventory";

export interface BatchImpactNode {
  id: string;
  type: BatchImpactNodeType;
  label: string;
  subtitle: string | null;
  status: string | null;
  severity: string | null;
  evidence_record_id: string | null;
  metadata: Record<string, unknown>;
  position_hint: string | null;
}

export interface BatchImpactEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  relationship_label: string;
  source_record_ids: string[];
  why_connected: string;
  limitation: string;
  confidence: string | null;
}

export interface BatchImpactSignal {
  name: string;
  category: string;
  level: "INFO" | "WATCH" | "ELEVATED" | "HIGH";
  explanation: string;
  evidence_record_ids: string[];
  confidence: string;
  recommended_assessment: string;
  limitation: string;
}

export interface BatchImpactSummary {
  primary_batch: string;
  related_batches: string[];
  similar_complaint_count: number;
  open_deviations: number;
  linked_capas: number;
  distributed_quantity: string;
  markets_or_locations: string[];
  remaining_inventory: string;
  suppliers_involved: string[];
  elevated_recurrence_signal: boolean;
  overall_investigation_priority: string;
  data_limitations: string[];
}

export interface RecommendedAssessment {
  title: string;
  rationale: string;
  evidence_record_ids: string[];
  limitation: string;
}

export interface BatchImpactResponse {
  run_id: string;
  nodes: BatchImpactNode[];
  edges: BatchImpactEdge[];
  signals: BatchImpactSignal[];
  impact_summary: BatchImpactSummary;
  recommended_assessments: RecommendedAssessment[];
  limitations: string[];
}

export interface ContainmentSimulationRequest {
  include_primary_batch: boolean;
  include_shared_packaging_lot: boolean;
  include_shared_material_lot: boolean;
  include_shared_equipment: boolean;
  equipment_date_window_days: number;
}

export interface ContainmentBatchScope {
  batch_number: string;
  product_name: string;
  inclusion_reasons: string[];
}

export interface ContainmentSimulationResponse {
  batches_included: ContainmentBatchScope[];
  internal_inventory_potentially_assessed: string;
  distributed_quantity: string;
  customers_or_markets_requiring_assessment: string[];
  open_shipments: string[];
  recommended_sample_checks: string[];
  possible_supply_impact: string;
  limitations: string[];
  simulation_only: true;
}
