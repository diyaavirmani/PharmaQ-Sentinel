import type {
  AssistantMessageState,
  ComplaintDraftFields,
  ComplaintFieldKey,
  ComplaintFieldState,
  ComplaintWorkspaceState,
  CompletenessState,
  ExtractionProgressState,
  RiskDetailsState,
  WorkspaceViewState
} from "../../types/complaintWorkspace";
import type {
  ComplaintDraftResponse,
  ComplaintDraftStatusResponse,
  ComplaintMessageResponse
} from "./complaintTypes";

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
  manufacturing_date_text: "manufacturingDate",
  expiry_retest_date: "expiryDate",
  expiry_retest_date_text: "expiryDate",
  quantity_affected: "quantityAffected",
  complaint_type: "complaintType",
  complaint_date: "complaintDate",
  detailed_description: "detailedComplaintDescription",
  suggested_severity: "initialSeverity",
  suggested_priority: "priority"
};

const uiFieldToServerField: Record<ComplaintFieldKey, string> = Object.fromEntries(
  Object.entries(serverFieldToUiField).map(([serverField, uiField]) => [uiField, serverField])
) as Record<ComplaintFieldKey, string>;
const uiEvidenceServerFields: Record<ComplaintFieldKey, string[]> = {
  complaintSource: ["complaint_source"],
  customerName: ["customer_name"],
  productName: ["product_name"],
  productStrengthGrade: ["product_strength_grade"],
  batchLotNumber: ["batch_lot_number"],
  manufacturingDate: ["manufacturing_date", "manufacturing_date_text"],
  expiryDate: ["expiry_retest_date", "expiry_retest_date_text"],
  quantityAffected: ["quantity_affected"],
  complaintType: ["complaint_type"],
  complaintDate: ["complaint_date"],
  detailedComplaintDescription: ["detailed_description"],
  initialSeverity: ["suggested_severity"],
  priority: ["suggested_priority"]
};

const baseAssistantMessage: AssistantMessageState = {
  id: "assistant-intake-ready",
  role: "assistant",
  content:
    "Upload a complaint document or paste text above. I will automatically extract the details and populate the form for you."
};

export function mapComplaintMessage(message: ComplaintMessageResponse): AssistantMessageState | null {
  if (message.role !== "USER" && message.role !== "ASSISTANT") {
    return null;
  }

  return {
    id: message.id,
    role: message.role === "USER" ? "user" : "assistant",
    content: message.message_text
  };
}

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
  evidenceFieldNames: Set<string>,
  extra?: Partial<ComplaintFieldState>
): ComplaintFieldState {
  const serverFieldName = uiFieldToServerField[fieldKey];
  const evidenceAvailable = uiEvidenceServerFields[fieldKey].some((fieldName) => evidenceFieldNames.has(fieldName));
  return {
    value,
    fieldName: serverFieldName,
    evidenceAvailable,
    recentlyUpdated: recentlyUpdatedFields.includes(fieldKey),
    ...extra
  };
}

export function mapDraftToFields(
  draft: ComplaintDraftResponse | null,
  recentlyUpdatedFields: ComplaintFieldKey[] = [],
  options?: { isLoading?: boolean; evidenceFieldNames?: string[] }
): ComplaintDraftFields {
  if (!draft) {
    return emptyFields({ isLoading: options?.isLoading });
  }
  const evidenceFieldNames = new Set(options?.evidenceFieldNames ?? []);

  return {
    complaintSource: buildField(draft.complaint_source, "complaintSource", recentlyUpdatedFields, evidenceFieldNames),
    customerName: buildField(draft.customer_name, "customerName", recentlyUpdatedFields, evidenceFieldNames),
    productName: buildField(draft.product_name, "productName", recentlyUpdatedFields, evidenceFieldNames),
    productStrengthGrade: buildField(
      draft.product_strength_grade,
      "productStrengthGrade",
      recentlyUpdatedFields,
      evidenceFieldNames
    ),
    batchLotNumber: buildField(draft.batch_lot_number, "batchLotNumber", recentlyUpdatedFields, evidenceFieldNames),
    manufacturingDate: buildField(
      draft.manufacturing_date ?? draft.manufacturing_date_text,
      "manufacturingDate",
      recentlyUpdatedFields,
      evidenceFieldNames
    ),
    expiryDate: buildField(
      draft.expiry_retest_date ?? draft.expiry_retest_date_text,
      "expiryDate",
      recentlyUpdatedFields,
      evidenceFieldNames
    ),
    quantityAffected: buildField(draft.quantity_affected, "quantityAffected", recentlyUpdatedFields, evidenceFieldNames, {
      unitSuffix: draft.quantity_unit ?? undefined
    }),
    complaintType: buildField(draft.complaint_type, "complaintType", recentlyUpdatedFields, evidenceFieldNames),
    complaintDate: buildField(draft.complaint_date, "complaintDate", recentlyUpdatedFields, evidenceFieldNames),
    detailedComplaintDescription: buildField(
      draft.detailed_description,
      "detailedComplaintDescription",
      recentlyUpdatedFields,
      evidenceFieldNames
    ),
    initialSeverity: buildField(titleCaseEnum(draft.suggested_severity), "initialSeverity", recentlyUpdatedFields, evidenceFieldNames),
    priority: buildField(titleCaseEnum(draft.suggested_priority), "priority", recentlyUpdatedFields, evidenceFieldNames)
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

export function statusLabel(status: string | null | undefined): "Pending Triage" | "Committed" {
  if (status === "COMMITTED") {
    return "Committed";
  }
  return "Pending Triage";
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function riskMetadata(draft: ComplaintDraftResponse | null): Record<string, unknown> | null {
  const risk = draft?.missing_fields?.risk;
  return typeof risk === "object" && risk !== null && !Array.isArray(risk) ? risk as Record<string, unknown> : null;
}

function completenessMetadata(draft: ComplaintDraftResponse | null): Record<string, unknown> | null {
  const completeness = draft?.missing_fields?.completeness;
  return typeof completeness === "object" && completeness !== null && !Array.isArray(completeness)
    ? completeness as Record<string, unknown>
    : null;
}

export function mapRiskDetails(draft: ComplaintDraftResponse | null): RiskDetailsState | null {
  if (!draft || !draft.suggested_severity) {
    return null;
  }
  const risk = riskMetadata(draft);
  return {
    confidence: draft.risk_confidence,
    oneLineRationale: typeof risk?.one_line_rationale === "string" ? risk.one_line_rationale : draft.risk_rationale,
    routeChips: asStringArray(risk?.route_chips ?? (draft.safety_route ? [draft.safety_route] : [])),
    requiresQaConfirmation: risk?.requires_qa_confirmation !== false,
    potentialHazards: asStringArray(risk?.potential_hazards ?? (draft.potential_hazard ? [draft.potential_hazard] : [])),
    supportingEvidence: asStringArray(risk?.supporting_evidence),
    contradictingEvidence: asStringArray(risk?.contradicting_evidence),
    recommendedActions: asStringArray(risk?.recommended_actions ?? (draft.suggested_next_action ? [draft.suggested_next_action] : [])),
    limitations: asStringArray(risk?.limitations),
    criticalSignals: asStringArray(risk?.critical_signals)
  };
}

export function mapCompleteness(draft: ComplaintDraftResponse | null): CompletenessState | null {
  const completeness = completenessMetadata(draft);
  if (!completeness) {
    return null;
  }
  const percentage = typeof completeness.completeness_percentage === "number" ? completeness.completeness_percentage : 0;
  const critical = asStringArray(completeness.missing_critical_fields);
  const recommended = asStringArray(completeness.missing_recommended_fields);
  return {
    percentage,
    missingItems: [...critical, ...recommended].slice(0, 3),
    followUpQuestions: asStringArray(completeness.targeted_follow_up_questions).slice(0, 3),
    canBeginTriage: completeness.can_begin_triage === true
  };
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
  messages?: AssistantMessageState[];
  evidenceFieldNames?: string[];
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
        isLoading: options.isLoading,
        evidenceFieldNames: options.evidenceFieldNames
      }),
      riskDetails: mapRiskDetails(options.draft),
      completeness: mapCompleteness(options.draft)
    },
    extraction: {
      stage,
      percentage,
      statusText: extractionStatusText(stage)
    },
    messages: options.messages?.length ? options.messages : [baseAssistantMessage],
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
    manufacturing_date_text: null,
    expiry_retest_date: "2026-06-01",
    expiry_retest_date_text: null,
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
    suggested_severity: "MAJOR",
    suggested_priority: "HIGH",
    safety_route: "PRODUCT_QUALITY",
    risk_rationale: "Visible capsule discolouration may indicate a product quality issue requiring QA review.",
    potential_hazard: "Potential product quality impact cannot be excluded from available information.",
    suggested_next_action: "Request sample return and complete missing patient-consumption details.",
    risk_confidence: "0.6200",
    missing_fields: {
      critical: [],
      recommended: ["sample availability", "patient consumption status", "reporter contact"],
      questions: [
        "Is a sample of the affected product available for return and laboratory inspection?",
        "Did any patient consume or use the product before the issue was noticed?"
      ],
      completeness: {
        completeness_percentage: 72,
        can_begin_triage: true,
        missing_critical_fields: [],
        missing_recommended_fields: ["sample availability", "patient consumption status", "reporter contact"],
        targeted_follow_up_questions: [
          "Is a sample of the affected product available for return and laboratory inspection?",
          "Did any patient consume or use the product before the issue was noticed?"
        ],
        blockers: [],
        warnings: []
      },
      risk: {
        route_chips: ["QUALITY_ASSURANCE"],
        case_type: "PRODUCT_QUALITY",
        confidence: 0.62,
        one_line_rationale: "Visible capsule discolouration may indicate a product quality issue requiring QA review.",
        potential_hazards: ["Potential product quality impact cannot be excluded from available information."],
        supporting_evidence: ["possible degradation from discolouration: discoloured"],
        contradicting_evidence: [],
        recommended_actions: ["Request sample return and complete missing patient-consumption details."],
        limitations: ["Draft recommendation requiring authorised QA review."],
        requires_qa_confirmation: true,
        deterministic_severity_floor: "MAJOR",
        critical_signals: []
      }
    },
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
