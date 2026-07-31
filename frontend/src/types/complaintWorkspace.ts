export type WorkspaceViewState = "empty" | "extracting" | "populated" | "error" | "edited";

export type ExtractionStage = "idle" | "uploading" | "extracting" | "complete" | "error";

export type ComplaintFieldKey =
  | "complaintSource"
  | "customerName"
  | "productName"
  | "productStrengthGrade"
  | "batchLotNumber"
  | "manufacturingDate"
  | "expiryDate"
  | "quantityAffected"
  | "complaintType"
  | "complaintDate"
  | "detailedComplaintDescription"
  | "initialSeverity"
  | "priority";

export interface ComplaintFieldState {
  value: string | null;
  fieldName?: string;
  unitSuffix?: string;
  evidenceAvailable?: boolean;
  recentlyUpdated?: boolean;
  isLoading?: boolean;
}

export type ComplaintDraftFields = Record<ComplaintFieldKey, ComplaintFieldState>;

export interface ComplaintDraftState {
  statusLabel: "Pending Triage" | "Committed";
  fields: ComplaintDraftFields;
  riskDetails: RiskDetailsState | null;
  completeness: CompletenessState | null;
}

export interface ExtractionProgressState {
  stage: ExtractionStage;
  percentage: number;
  statusText: string;
}

export type AssistantMessageRole = "assistant" | "user";

export interface AssistantMessageState {
  id: string;
  role: AssistantMessageRole;
  content: string;
}

export interface RiskDetailsState {
  confidence: string | null;
  oneLineRationale: string | null;
  routeChips: string[];
  requiresQaConfirmation: boolean;
  potentialHazards: string[];
  supportingEvidence: string[];
  contradictingEvidence: string[];
  recommendedActions: string[];
  limitations: string[];
  criticalSignals: string[];
}

export interface CompletenessState {
  percentage: number;
  missingItems: string[];
  followUpQuestions: string[];
  canBeginTriage: boolean;
}

export interface ComplaintWorkspaceState {
  viewState: WorkspaceViewState;
  draft: ComplaintDraftState;
  extraction: ExtractionProgressState;
  messages: AssistantMessageState[];
  showQualityDock: boolean;
}
