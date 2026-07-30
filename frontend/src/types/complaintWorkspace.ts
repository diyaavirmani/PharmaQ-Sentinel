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
  unitSuffix?: string;
  evidenceAvailable?: boolean;
  recentlyUpdated?: boolean;
  isLoading?: boolean;
}

export type ComplaintDraftFields = Record<ComplaintFieldKey, ComplaintFieldState>;

export interface ComplaintDraftState {
  statusLabel: "Pending Triage";
  fields: ComplaintDraftFields;
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

export interface ComplaintWorkspaceState {
  viewState: WorkspaceViewState;
  draft: ComplaintDraftState;
  extraction: ExtractionProgressState;
  messages: AssistantMessageState[];
  showQualityDock: boolean;
}
