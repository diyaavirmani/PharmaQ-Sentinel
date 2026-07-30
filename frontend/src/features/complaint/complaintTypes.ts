import type {
  AssistantMessageState,
  ComplaintDraftState,
  ComplaintFieldKey,
  ExtractionStage
} from "../../types/complaintWorkspace";

export type ComplaintDraftStatus =
  | "DRAFT"
  | "PENDING_TRIAGE"
  | "AWAITING_INFORMATION"
  | "UNDER_QA_REVIEW"
  | "UNDER_INVESTIGATION"
  | "COMMITTED"
  | "CLOSED"
  | "CANCELLED";

export type IntelligenceTab =
  | "Batch Intelligence"
  | "Quality War Room"
  | "Evidence & Audit"
  | "Investigation Support";

export interface ComplaintDraftResponse {
  id: string;
  thread_id: string;
  status: ComplaintDraftStatus;
  created_by: string | null;
  complaint_source: string | null;
  customer_name: string | null;
  customer_contact: string | null;
  country_market: string | null;
  product_type: string | null;
  product_name: string | null;
  product_strength_grade: string | null;
  dosage_form: string | null;
  batch_lot_number: string | null;
  manufacturing_date: string | null;
  expiry_retest_date: string | null;
  quantity_affected: string | null;
  quantity_unit: string | null;
  complaint_type: string | null;
  complaint_date: string | null;
  detailed_description: string | null;
  defect_observed_date: string | null;
  sample_available: boolean | null;
  patient_consumed_product: boolean | null;
  adverse_event_signal: boolean | null;
  counterfeit_signal: boolean | null;
  storage_conditions: string | null;
  suggested_severity: string | null;
  suggested_priority: string | null;
  safety_route: string | null;
  risk_rationale: string | null;
  potential_hazard: string | null;
  suggested_next_action: string | null;
  risk_confidence: string | null;
  missing_fields: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  is_locked: boolean;
  is_committed: boolean;
  is_extraction_active: boolean;
}

export interface ComplaintDraftStatusResponse {
  id: string;
  status: ComplaintDraftStatus;
  updated_at: string;
  is_locked: boolean;
  is_committed: boolean;
  is_extraction_active: boolean;
}

export interface CreateComplaintDraftRequest {
  created_by: string;
}

export type DevelopmentPatchFields = Partial<{
  complaint_source: string | null;
  customer_name: string | null;
  customer_contact: string | null;
  country_market: string | null;
  product_type: "API" | "FDF" | "UNKNOWN" | null;
  product_name: string | null;
  product_strength_grade: string | null;
  dosage_form: string | null;
  batch_lot_number: string | null;
  manufacturing_date: string | null;
  expiry_retest_date: string | null;
  quantity_affected: string | null;
  quantity_unit: string | null;
  complaint_type: string | null;
  complaint_date: string | null;
  detailed_description: string | null;
  defect_observed_date: string | null;
  sample_available: boolean | null;
  patient_consumed_product: boolean | null;
  adverse_event_signal: boolean | null;
  counterfeit_signal: boolean | null;
  storage_conditions: string | null;
  suggested_severity: "CRITICAL" | "MAJOR" | "MINOR" | "UNDETERMINED" | null;
  suggested_priority: "IMMEDIATE" | "HIGH" | "NORMAL" | "LOW" | "UNDETERMINED" | null;
  safety_route:
    | "PRODUCT_QUALITY"
    | "POSSIBLE_ADVERSE_EVENT"
    | "QUALITY_AND_ADVERSE_EVENT"
    | "COUNTERFEIT_OR_TAMPERING"
    | "DISTRIBUTION_OR_STORAGE"
    | "SERVICE_ONLY"
    | "UNDETERMINED"
    | null;
  risk_rationale: string | null;
  potential_hazard: string | null;
  suggested_next_action: string | null;
  risk_confidence: string | null;
  missing_fields: Record<string, unknown> | null;
}>;

export interface DevelopmentPatchRequest {
  patch: DevelopmentPatchFields;
  actor_identifier?: string;
  reason?: string;
  source?: string;
}

export interface ComplaintSliceState {
  activeDraftId: string | null;
  complaintDraft: ComplaintDraftResponse | null;
  draftStatus: ComplaintDraftStatusResponse | null;
  isCreatingDraft: boolean;
  isLoadingDraft: boolean;
  isResettingDraft: boolean;
  draftError: string | null;
  draftInfoMessage: string | null;
  draftSuccessMessage: string | null;
  recentlyUpdatedFields: ComplaintFieldKey[];
  extractionStage: ExtractionStage;
  extractionProgress: number;
  isComposerLocked: boolean;
  activeIntelligenceTab: IntelligenceTab;
  isIntelligenceDockExpanded: boolean;
}

export interface ComplaintWorkspaceViewModel {
  draft: ComplaintDraftState;
  messages: AssistantMessageState[];
  extractionStage: ExtractionStage;
  extractionProgress: number;
  extractionStatusText: string;
  showQualityDock: boolean;
}
