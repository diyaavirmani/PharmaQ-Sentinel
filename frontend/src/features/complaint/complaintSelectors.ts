import type { RootState } from "../../app/store";
import { isDraftEmpty, missingFieldNames } from "./complaintMappers";

export const selectComplaintState = (state: RootState) => state.complaint;

export const selectActiveComplaint = (state: RootState) => selectComplaintState(state).complaintDraft;

export const selectActiveDraftId = (state: RootState) => selectComplaintState(state).activeDraftId;

export const selectIsComplaintFormEmpty = (state: RootState) => isDraftEmpty(selectActiveComplaint(state));

export const selectShouldEnableSaveComplaint = (state: RootState) => {
  const complaintState = selectComplaintState(state);
  const draft = complaintState.complaintDraft;
  if (!draft || draft.is_locked || draft.is_committed) {
    return false;
  }
  if (complaintState.isCreatingDraft || complaintState.isLoadingDraft || complaintState.isSavingComplaint) {
    return false;
  }
  if (complaintState.extractionStage === "uploading" || complaintState.extractionStage === "extracting") {
    return false;
  }
  if (complaintState.draftStatus?.is_extraction_active || complaintState.hasCriticalEvidenceConflict) {
    return false;
  }
  const hasDescription = Boolean(draft.detailed_description?.trim());
  const hasProductIdentification = Boolean(draft.product_name?.trim() || draft.batch_lot_number?.trim());
  const hasRiskAssessment = Boolean(draft.suggested_severity && draft.risk_rationale);
  return hasDescription && hasProductIdentification && hasRiskAssessment;
};

export const selectRecentlyUpdatedFields = (state: RootState) =>
  selectComplaintState(state).recentlyUpdatedFields;

export const selectCurrentStatusBadge = (state: RootState) => {
  const status = selectActiveComplaint(state)?.status ?? "DRAFT";
  if (status === "COMMITTED") {
    return "Committed";
  }
  return "Pending Triage";
};

export const selectMissingFieldNames = (state: RootState) => missingFieldNames(selectActiveComplaint(state));

export const selectCurrentRiskAssessment = (state: RootState) => {
  const draft = selectActiveComplaint(state);
  return {
    severity: draft?.suggested_severity ?? null,
    priority: draft?.suggested_priority ?? null,
    rationale: draft?.risk_rationale ?? null,
    confidence: draft?.risk_confidence ?? null
  };
};

export const selectIsAdvancedIntelligenceAvailable = (state: RootState) => {
  const complaintState = selectComplaintState(state);
  return !isDraftEmpty(complaintState.complaintDraft) || complaintState.extractionStage === "extracting";
};
