import type {
  AssistantMessageState,
  ComplaintDraftFields,
  ComplaintFieldKey,
  ComplaintFieldState,
  ComplaintWorkspaceState,
  ExtractionProgressState,
  WorkspaceViewState
} from "../../types/complaintWorkspace";
import type { ComplaintDraftResponse, ComplaintDraftStatusResponse } from "./complaintTypes";

export const emptyFieldKeys: ComplaintFieldKey[] = [
  "complaintSource",
  "customerName",
  "productName",
  "productStrengthGrade",
  "batchLotNumber",
  "manufacturingDate",
  "expiryDate",
  "quantityAffected",
  "complaintType",
  "complaintDate",
  "detailedComplaintDescription",
  "initialSeverity",
  "priority"
];

export const fieldLabels: Record<ComplaintFieldKey, string> = {
  complaintSource: "Complaint Source",
  customerName: "Customer Name",
  productName: "Product Name",
  productStrengthGrade: "Product Strength/Grade",
  batchLotNumber: "Batch/Lot Number",
  manufacturingDate: "Manufacturing Date",
  expiryDate: "Expiry Date",
  quantityAffected: "Quantity Affected",
  complaintType: "Complaint Type",
  complaintDate: "Complaint Date",
  detailedComplaintDescription: "Detailed Complaint Description",
  initialSeverity: "Initial Severity",
  priority: "Priority"
};

export const serverFieldToUiField: Record<string, ComplaintFieldKey> = {
  complaint_source: "complaintSource",
  customer_name: "customerName",
  product_name: "productName",
  product_strength_grade: "productStrengthGrade",
  batch_lot_number: "batchLotNumber",
  manufacturing_date: "manufacturingDate",
  expiry_retest_date: "expiryDate",
  quantity_affected: "quantityAffected",
  complaint_type: "complaintType",
  complaint_date: "complaintDate",
  detailed_description: "detailedComplaintDescription",
  suggested_severity: "initialSeverity",
  suggested_priority: "priority"
};

const baseAssistantMessage: AssistantMessageState = {
  id: "assistant-intake-ready",
  role: "assistant",
  content:
    "Upload a complaint document or paste text above. I will automatically extract the details and populate the form for you."
};

function titleCaseEnum(value: string | null): string | null {
  if (!value) {
    return null;
  }

  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function emptyFields(options?: { isLoading?: boolean }): ComplaintDraftFields {
  return Object.fromEntries(
    emptyFieldKeys.map((fieldKey) => [fieldKey, { value: null, isLoading: options?.isLoading }])
  ) as ComplaintDraftFields;
}

function buildField(
  value: string | null,
  fieldKey: ComplaintFieldKey,
  recentlyUpdatedFields: ComplaintFieldKey[],
  extra?: Partial<ComplaintFieldState>
): ComplaintFieldState {
  return {
    value,
    recentlyUpdated: recentlyUpdatedFields.includes(fieldKey),
    ...extra
  };
}

export function mapDraftToFields(
  draft: ComplaintDraftResponse | null,
  recentlyUpdatedFields: ComplaintFieldKey[] = [],
  options?: { isLoading?: boolean }
): ComplaintDraftFields {
  if (!draft) {
    return emptyFields({ isLoading: options?.isLoading });
  }

  return {
    complaintSource: buildField(draft.complaint_source, "complaintSource", recentlyUpdatedFields),
    customerName: buildField(draft.customer_name, "customerName", recentlyUpdatedFields),
    productName: buildField(draft.product_name, "productName", recentlyUpdatedFields),
    productStrengthGrade: buildField(
      draft.product_strength_grade,
      "productStrengthGrade",
      recentlyUpdatedFields
    ),
    batchLotNumber: buildField(draft.batch_lot_number, "batchLotNumber", recentlyUpdatedFields),
    manufacturingDate: buildField(draft.manufacturing_date, "manufacturingDate", recentlyUpdatedFields),
    expiryDate: buildField(draft.expiry_retest_date, "expiryDate", recentlyUpdatedFields),
    quantityAffected: buildField(draft.quantity_affected, "quantityAffected", recentlyUpdatedFields, {
      unitSuffix: draft.quantity_unit ?? undefined
    }),
    complaintType: buildField(draft.complaint_type, "complaintType", recentlyUpdatedFields),
    complaintDate: buildField(draft.complaint_date, "complaintDate", recentlyUpdatedFields),
    detailedComplaintDescription: buildField(
      draft.detailed_description,
      "detailedComplaintDescription",
      recentlyUpdatedFields
    ),
    initialSeverity: buildField(titleCaseEnum(draft.suggested_severity), "initialSeverity", recentlyUpdatedFields),
    priority: buildField(titleCaseEnum(draft.suggested_priority), "priority", recentlyUpdatedFields)
  };
}

export function isDraftEmpty(draft: ComplaintDraftResponse | null): boolean {
  if (!draft) {
    return true;
  }

  return [
    draft.complaint_source,
    draft.customer_name,
    draft.product_name,
    draft.product_strength_grade,
    draft.batch_lot_number,
    draft.manufacturing_date,
    draft.expiry_retest_date,
    draft.quantity_affected,
    draft.complaint_type,
    draft.complaint_date,
    draft.detailed_description,
    draft.suggested_severity,
    draft.suggested_priority
  ].every((value) => value === null || value === "");
}

export function statusLabel(_status: string | null | undefined): "Pending Triage" {
  return "Pending Triage";
}

export function extractionStatusText(stage: ExtractionProgressState["stage"]): string {
  if (stage === "extracting") {
    return "Extracting complaint details from the submitted source.";
  }
  if (stage === "complete") {
    return "Draft fields populated for review.";
  }
  if (stage === "error") {
    return "Extraction could not be completed for this source.";
  }
  return "Waiting for complaint source.";
}

export function mapDraftToWorkspaceState(options: {
  draft: ComplaintDraftResponse | null;
  draftStatus: ComplaintDraftStatusResponse | null;
  recentlyUpdatedFields: ComplaintFieldKey[];
  extractionStage: ExtractionProgressState["stage"];
  extractionProgress: number;
  isLoading?: boolean;
}): ComplaintWorkspaceState {
  const stage = options.draftStatus?.is_extraction_active ? "extracting" : options.extractionStage;
  const percentage = options.draftStatus?.is_extraction_active ? 62 : options.extractionProgress;
  const viewState: WorkspaceViewState = isDraftEmpty(options.draft)
    ? stage === "extracting"
      ? "extracting"
      : "empty"
    : options.recentlyUpdatedFields.length > 0
      ? "edited"
      : "populated";

  return {
    viewState,
    draft: {
      statusLabel: statusLabel(options.draft?.status ?? null),
      fields: mapDraftToFields(options.draft, options.recentlyUpdatedFields, {
        isLoading: options.isLoading
      })
    },
    extraction: {
      stage,
      percentage,
      statusText: extractionStatusText(stage)
    },
    messages: [baseAssistantMessage],
    showQualityDock: !isDraftEmpty(options.draft) || stage === "extracting"
  };
}

export function createVisualRegressionState(viewState: WorkspaceViewState): ComplaintWorkspaceState {
  const populatedDraft: ComplaintDraftResponse = {
    id: "visual-draft-id",
    thread_id: "visual-thread-id",
    status: "DRAFT",
    created_by: "Demo User",
    complaint_source: "Email-style complaint text",
    customer_name: "Demo Quality Contact",
    customer_contact: null,
    country_market: null,
    product_type: "FDF",
    product_name: "Amoxicillin Capsules 500 mg",
    product_strength_grade: "500 mg",
    dosage_form: null,
    batch_lot_number: "BMX240602",
    manufacturing_date: "2024-06-02",
    expiry_retest_date: "2026-06-01",
    quantity_affected: "12",
    quantity_unit: "packs",
    complaint_type: "Capsule discolouration",
    complaint_date: "2026-07-30",
    detailed_description: "Customer reported visible colour variation in multiple capsules from one blister strip.",
    defect_observed_date: null,
    sample_available: null,
    patient_consumed_product: null,
    adverse_event_signal: null,
    counterfeit_signal: null,
    storage_conditions: null,
    suggested_severity: "UNDETERMINED",
    suggested_priority: "UNDETERMINED",
    safety_route: null,
    risk_rationale: null,
    potential_hazard: null,
    suggested_next_action: null,
    risk_confidence: null,
    missing_fields: null,
    created_at: "2026-07-30T00:00:00Z",
    updated_at: "2026-07-30T00:00:00Z",
    is_locked: false,
    is_committed: false,
    is_extraction_active: false
  };

  if (viewState === "empty") {
    return mapDraftToWorkspaceState({
      draft: null,
      draftStatus: null,
      recentlyUpdatedFields: [],
      extractionStage: "idle",
      extractionProgress: 0
    });
  }

  if (viewState === "extracting") {
    return mapDraftToWorkspaceState({
      draft: null,
      draftStatus: { ...populatedDraft, updated_at: populatedDraft.updated_at, is_extraction_active: true },
      recentlyUpdatedFields: [],
      extractionStage: "extracting",
      extractionProgress: 62
    });
  }

  if (viewState === "edited") {
    const editedState = mapDraftToWorkspaceState({
      draft: populatedDraft,
      draftStatus: null,
      recentlyUpdatedFields: ["batchLotNumber", "quantityAffected"],
      extractionStage: "complete",
      extractionProgress: 100
    });
    return {
      ...editedState,
      extraction: {
        ...editedState.extraction,
        statusText: "Recent assistant correction applied to highlighted fields."
      }
    };
  }

  return mapDraftToWorkspaceState({
    draft: populatedDraft,
    draftStatus: null,
    recentlyUpdatedFields: [],
    extractionStage: viewState === "error" ? "error" : "complete",
    extractionProgress: viewState === "error" ? 18 : 100
  });
}

export function missingFieldNames(draft: ComplaintDraftResponse | null): string[] {
  const fields = mapDraftToFields(draft);
  return emptyFieldKeys.filter((fieldKey) => fields[fieldKey].value === null).map((fieldKey) => fieldLabels[fieldKey]);
}
