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
  manufacturing_date_text: string | null;
  expiry_retest_date: string | null;
  expiry_retest_date_text: string | null;
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

export interface ComplaintAttachmentUploadResponse {
  attachment_id: string;
  original_filename: string;
  status: "PENDING" | "VALIDATING" | "EXTRACTING" | "COMPLETE" | "FAILED";
  progress_percentage: number;
  current_stage: string;
  duplicate: boolean;
  changed_fields: string[];
  created_at: string;
}

export interface ComplaintAttachmentStatusResponse {
  attachment_id: string;
  original_filename: string;
  status: "PENDING" | "VALIDATING" | "EXTRACTING" | "COMPLETE" | "FAILED";
  progress_percentage: number;
  current_stage: string;
  safe_error: string | null;
  created_at: string;
  completed_at: string | null;
}

export type EvidenceStatus =
  | "EXPLICIT_SOURCE"
  | "NORMALISED_SOURCE"
  | "AI_INFERENCE"
  | "USER_CORRECTION"
  | "SYSTEM_REFERENCE"
  | "CONFLICTING_SOURCE"
  | "SUPERSEDED";

export interface EvidenceSourceMessage {
  id: string;
  role: string;
  message_text: string;
  created_at: string;
}

export interface EvidenceSourceAttachment {
  id: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  sha256_checksum: string;
  extraction_status: string;
  created_at: string;
  uploaded_by: string | null;
}

export interface FieldEvidenceResponse {
  id: string;
  draft_id: string;
  field_name: string;
  field_value: Record<string, unknown> | null;
  display_value: unknown;
  evidence_type: string;
  evidence_status: EvidenceStatus;
  conflict_status: string;
  active_reason: string | null;
  source_message_id: string | null;
  source_attachment_id: string | null;
  source_message: EvidenceSourceMessage | null;
  source_attachment: EvidenceSourceAttachment | null;
  page_number: number | null;
  paragraph_index: number | null;
  source_excerpt: string | null;
  confidence: string | null;
  extraction_method: string | null;
  is_explicit: boolean;
  is_normalised: boolean;
  is_inferred: boolean;
  is_active: boolean;
  provider_name: string | null;
  actual_model: string | null;
  created_at: string;
}

export interface EvidenceConflictResponse {
  field_name: string;
  is_critical: boolean;
  current_value: unknown;
  active_evidence_id: string | null;
  conflicting_evidence_ids: string[];
  active_reason: string;
  description: string;
}

export interface FieldEvidenceListResponse {
  items: FieldEvidenceResponse[];
  limit: number;
  offset: number;
  next_offset: number | null;
  conflicts: EvidenceConflictResponse[];
  critical_conflicts_block_save: boolean;
}

export interface FieldEvidenceDetailResponse {
  field_name: string;
  current_value: unknown;
  current_active_evidence: FieldEvidenceResponse | null;
  evidence_history: FieldEvidenceResponse[];
  conflicts: EvidenceConflictResponse[];
  critical_conflict_unresolved: boolean;
}

export interface TimelineEntryResponse {
  event_id: string;
  event_type: string;
  actor: string;
  timestamp: string;
  title: string;
  description: string;
  affected_fields: string[];
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  evidence_references: string[];
  attachment_references: string[];
  provider_name: string | null;
  actual_model: string | null;
}

export interface TimelineListResponse {
  items: TimelineEntryResponse[];
  limit: number;
  offset: number;
  next_offset: number | null;
}

export interface SaveComplaintRequest {
  reviewed_by: string;
  review_meaning: string;
  missing_information_acknowledged: boolean;
  change_reason: string;
  idempotency_key: string;
}

export interface ComplaintResponse {
  id: string;
  complaint_number: string;
  current_version_number: number;
  status: ComplaintDraftStatus;
  committed_from_draft_id: string | null;
  committed_at: string;
  committed_by: string;
  review_meaning: string | null;
  missing_information_acknowledged: boolean;
  unresolved_missing_information: Record<string, unknown> | null;
  latest_risk_assessment_id: string | null;
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
  manufacturing_date_text: string | null;
  expiry_retest_date: string | null;
  expiry_retest_date_text: string | null;
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
}

export interface ComplaintLedgerListResponse {
  items: ComplaintResponse[];
  limit: number;
  offset: number;
  next_offset: number | null;
}

export interface ComplaintMessageResponse {
  id: string;
  draft_id: string;
  role: "USER" | "ASSISTANT" | "SYSTEM" | "TOOL";
  message_text: string;
  attachment_id: string | null;
  created_at: string;
  metadata_json: Record<string, unknown> | null;
}

export interface ComplaintMessageListResponse {
  messages: ComplaintMessageResponse[];
  limit: number;
  offset: number;
  next_offset: number | null;
}

export interface SendComplaintMessageRequest {
  message: string;
  attachment_id: string | null;
}

export interface SendComplaintMessageResponse {
  user_message: ComplaintMessageResponse;
  assistant_message: ComplaintMessageResponse;
  intent:
    | "LOG_COMPLAINT"
    | "EDIT_COMPLAINT"
    | "EXTRACT_DOCUMENT"
    | "ASK_QUESTION"
    | "REQUEST_SUMMARY"
    | "RUN_BATCH_IMPACT"
    | "RUN_QUALITY_WAR_ROOM"
    | "SAVE_COMPLAINT"
    | "UNKNOWN";
  tool_name: string | null;
  draft: ComplaintDraftResponse;
  changed_fields: string[];
  warnings: string[];
  clarification_required: boolean;
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
  manufacturing_date_text: string | null;
  expiry_retest_date: string | null;
  expiry_retest_date_text: string | null;
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
  isSavingComplaint: boolean;
  draftError: string | null;
  draftInfoMessage: string | null;
  draftSuccessMessage: string | null;
  assistantMessages: AssistantMessageState[];
  isSendingMessage: boolean;
  activeAttachmentId: string | null;
  selectedUploadFilename: string | null;
  uploadError: string | null;
  hasCriticalEvidenceConflict: boolean;
  committedComplaint: ComplaintResponse | null;
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
