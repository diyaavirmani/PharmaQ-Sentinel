import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { ComplaintFieldKey, ExtractionStage } from "../../types/complaintWorkspace";
import { complaintApi } from "./complaintApi";
import { mapComplaintMessage, serverFieldToUiField } from "./complaintMappers";
import type { ComplaintSliceState, IntelligenceTab } from "./complaintTypes";

const initialState: ComplaintSliceState = {
  activeDraftId: null,
  complaintDraft: null,
  draftStatus: null,
  isCreatingDraft: false,
  isLoadingDraft: false,
  isResettingDraft: false,
  isSavingComplaint: false,
  draftError: null,
  draftInfoMessage: null,
  draftSuccessMessage: null,
  assistantMessages: [],
  isSendingMessage: false,
  activeAttachmentId: null,
  selectedUploadFilename: null,
  uploadError: null,
  hasCriticalEvidenceConflict: false,
  committedComplaint: null,
  recentlyUpdatedFields: [],
  extractionStage: "idle",
  extractionProgress: 0,
  isComposerLocked: false,
  activeIntelligenceTab: "Batch Intelligence",
  isIntelligenceDockExpanded: false
};

function errorMessageFromPayload(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && "data" in payload) {
    const data = (payload as { data?: unknown }).data;
    if (typeof data === "object" && data !== null && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
  }

  return fallback;
}

function updatedFieldsFromPatch(patch: Record<string, unknown>): ComplaintFieldKey[] {
  return Object.keys(patch)
    .map((fieldName) => serverFieldToUiField[fieldName])
    .filter((fieldName): fieldName is ComplaintFieldKey => Boolean(fieldName));
}

function updatedFieldsFromServerFields(fields: string[]): ComplaintFieldKey[] {
  return fields
    .map((fieldName) => serverFieldToUiField[fieldName])
    .filter((fieldName): fieldName is ComplaintFieldKey => Boolean(fieldName));
}

function stageFromAttachmentStage(stage: string, status: string): ExtractionStage {
  if (status === "FAILED") {
    return "error";
  }
  if (status === "COMPLETE") {
    return "complete";
  }
  if (stage === "UPLOADING" || stage === "VALIDATING" || stage === "SAVING_ORIGINAL") {
    return "uploading";
  }
  return "extracting";
}

export const complaintSlice = createSlice({
  name: "complaint",
  initialState,
  reducers: {
    setActiveDraftId(state, action: PayloadAction<string | null>) {
      state.activeDraftId = action.payload;
    },
    setDraftInfoMessage(state, action: PayloadAction<string | null>) {
      state.draftInfoMessage = action.payload;
    },
    setDraftSuccessMessage(state, action: PayloadAction<string | null>) {
      state.draftSuccessMessage = action.payload;
    },
    clearDraftError(state) {
      state.draftError = null;
    },
    setExtractionState(
      state,
      action: PayloadAction<{ stage: ExtractionStage; progress: number }>
    ) {
      state.extractionStage = action.payload.stage;
      state.extractionProgress = action.payload.progress;
    },
    setComposerLocked(state, action: PayloadAction<boolean>) {
      state.isComposerLocked = action.payload;
    },
    setActiveIntelligenceTab(state, action: PayloadAction<IntelligenceTab>) {
      state.activeIntelligenceTab = action.payload;
    },
    setIntelligenceDockExpanded(state, action: PayloadAction<boolean>) {
      state.isIntelligenceDockExpanded = action.payload;
    }
  },
  extraReducers: (builder) => {
    builder
      .addMatcher(complaintApi.endpoints.createComplaintDraft.matchPending, (state) => {
        state.isCreatingDraft = true;
        state.draftError = null;
        state.draftSuccessMessage = null;
      })
      .addMatcher(complaintApi.endpoints.createComplaintDraft.matchFulfilled, (state, action) => {
        state.isCreatingDraft = false;
        state.activeDraftId = action.payload.id;
        state.complaintDraft = action.payload;
        state.draftStatus = null;
        state.recentlyUpdatedFields = [];
        state.extractionStage = "idle";
        state.extractionProgress = 0;
      })
      .addMatcher(complaintApi.endpoints.createComplaintDraft.matchRejected, (state, action) => {
        state.isCreatingDraft = false;
        state.draftError = errorMessageFromPayload(action.payload, "Could not create complaint draft.");
      })
      .addMatcher(complaintApi.endpoints.getComplaintDraft.matchPending, (state) => {
        state.isLoadingDraft = true;
        state.draftError = null;
      })
      .addMatcher(complaintApi.endpoints.getComplaintDraft.matchFulfilled, (state, action) => {
        state.isLoadingDraft = false;
        state.activeDraftId = action.payload.id;
        state.complaintDraft = action.payload;
      })
      .addMatcher(complaintApi.endpoints.getComplaintDraft.matchRejected, (state, action) => {
        state.isLoadingDraft = false;
        state.draftError = errorMessageFromPayload(action.payload, "Could not load complaint draft.");
      })
      .addMatcher(complaintApi.endpoints.resetComplaintDraft.matchPending, (state) => {
        state.isResettingDraft = true;
        state.draftError = null;
        state.draftSuccessMessage = null;
      })
      .addMatcher(complaintApi.endpoints.resetComplaintDraft.matchFulfilled, (state, action) => {
        state.isResettingDraft = false;
        state.activeDraftId = action.payload.id;
        state.complaintDraft = action.payload;
        state.committedComplaint = null;
        state.hasCriticalEvidenceConflict = false;
        state.recentlyUpdatedFields = [];
        state.extractionStage = "idle";
        state.extractionProgress = 0;
        state.activeAttachmentId = null;
        state.selectedUploadFilename = null;
        state.uploadError = null;
        state.draftSuccessMessage = "Complaint draft values cleared.";
      })
      .addMatcher(complaintApi.endpoints.resetComplaintDraft.matchRejected, (state, action) => {
        state.isResettingDraft = false;
        state.draftError = errorMessageFromPayload(action.payload, "Could not reset complaint draft.");
      })
      .addMatcher(complaintApi.endpoints.getComplaintDraftStatus.matchFulfilled, (state, action) => {
        state.draftStatus = action.payload;
        if (action.payload.is_extraction_active) {
          state.extractionStage = "extracting";
          state.extractionProgress = 62;
        }
        if (action.payload.is_committed) {
          state.isComposerLocked = true;
        }
      })
      .addMatcher(complaintApi.endpoints.getComplaintEvidence.matchFulfilled, (state, action) => {
        state.hasCriticalEvidenceConflict = action.payload.critical_conflicts_block_save;
      })
      .addMatcher(complaintApi.endpoints.getComplaintMessages.matchFulfilled, (state, action) => {
        const messages = Array.isArray(action.payload.messages) ? action.payload.messages : [];
        state.assistantMessages = messages
          .map(mapComplaintMessage)
          .filter((message): message is NonNullable<typeof message> => Boolean(message));
      })
      .addMatcher(complaintApi.endpoints.uploadComplaintAttachment.matchPending, (state, action) => {
        state.activeAttachmentId = null;
        state.selectedUploadFilename = action.meta.arg.originalArgs.file.name;
        state.uploadError = null;
        state.draftError = null;
        state.draftSuccessMessage = null;
        state.isComposerLocked = true;
        state.extractionStage = "uploading";
        state.extractionProgress = 10;
      })
      .addMatcher(complaintApi.endpoints.uploadComplaintAttachment.matchFulfilled, (state, action) => {
        state.activeAttachmentId = action.payload.attachment_id;
        state.selectedUploadFilename = action.payload.original_filename;
        state.uploadError = null;
        state.isComposerLocked = action.payload.status !== "COMPLETE" && action.payload.status !== "FAILED";
        state.extractionStage = stageFromAttachmentStage(action.payload.current_stage, action.payload.status);
        state.extractionProgress = action.payload.progress_percentage;
        state.recentlyUpdatedFields = updatedFieldsFromServerFields(action.payload.changed_fields);
        if (action.payload.draft) {
          state.activeDraftId = action.payload.draft.id;
          state.complaintDraft = action.payload.draft;
        }
        state.draftSuccessMessage =
          action.payload.status === "COMPLETE"
            ? "Document extraction completed."
            : action.payload.duplicate
              ? "This document was already uploaded for this draft."
              : null;
      })
      .addMatcher(complaintApi.endpoints.uploadComplaintAttachment.matchRejected, (state, action) => {
        state.isComposerLocked = false;
        state.extractionStage = "error";
        state.extractionProgress = 100;
        state.uploadError = errorMessageFromPayload(action.payload, "Could not upload complaint document.");
        state.draftError = state.uploadError;
      })
      .addMatcher(complaintApi.endpoints.getComplaintAttachmentStatus.matchFulfilled, (state, action) => {
        state.activeAttachmentId = action.payload.attachment_id;
        state.selectedUploadFilename = action.payload.original_filename;
        state.extractionStage = stageFromAttachmentStage(action.payload.current_stage, action.payload.status);
        state.extractionProgress = action.payload.progress_percentage;
        state.isComposerLocked = action.payload.status !== "COMPLETE" && action.payload.status !== "FAILED";
        if (action.payload.status === "FAILED") {
          state.uploadError = action.payload.safe_error ?? "Document extraction could not be completed.";
          state.draftError = state.uploadError;
        }
        if (action.payload.status === "COMPLETE") {
          state.uploadError = null;
          state.draftSuccessMessage = "Document extraction completed.";
        }
      })
      .addMatcher(complaintApi.endpoints.sendComplaintMessage.matchPending, (state, action) => {
        state.isSendingMessage = true;
        state.isComposerLocked = true;
        state.extractionStage = "extracting";
        state.extractionProgress = 20;
        state.draftError = null;
        const content = action.meta.arg.originalArgs.body.message.trim();
        if (content) {
          state.assistantMessages.push({
            id: `pending-user-${Date.now()}`,
            role: "user",
            content
          });
        }
      })
      .addMatcher(complaintApi.endpoints.sendComplaintMessage.matchFulfilled, (state, action) => {
        const serverMessages = [action.payload.user_message, action.payload.assistant_message]
          .map(mapComplaintMessage)
          .filter((message): message is NonNullable<typeof message> => Boolean(message));
        state.isSendingMessage = false;
        state.isComposerLocked = false;
        state.complaintDraft = action.payload.draft;
        state.assistantMessages = [
          ...state.assistantMessages.filter((message) => !message.id.startsWith("pending-user-")),
          ...serverMessages
        ];
        state.recentlyUpdatedFields = updatedFieldsFromServerFields(action.payload.changed_fields);
        state.extractionStage = "complete";
        state.extractionProgress = 100;
      })
      .addMatcher(complaintApi.endpoints.sendComplaintMessage.matchRejected, (state, action) => {
        state.isSendingMessage = false;
        state.isComposerLocked = false;
        state.extractionStage = "error";
        state.extractionProgress = 100;
        state.draftError = errorMessageFromPayload(action.payload, "Could not send assistant message.");
      })
      .addMatcher(complaintApi.endpoints.saveComplaintDraft.matchPending, (state) => {
        state.isSavingComplaint = true;
        state.draftError = null;
        state.draftSuccessMessage = null;
      })
      .addMatcher(complaintApi.endpoints.saveComplaintDraft.matchFulfilled, (state, action) => {
        state.isSavingComplaint = false;
        state.committedComplaint = action.payload;
        state.draftSuccessMessage = `Complaint ${action.payload.complaint_number} saved to the demonstration QMS ledger.`;
        state.isComposerLocked = true;
        if (state.complaintDraft && state.complaintDraft.id === action.payload.committed_from_draft_id) {
          state.complaintDraft.status = "COMMITTED";
          state.complaintDraft.is_locked = true;
          state.complaintDraft.is_committed = true;
          state.complaintDraft.updated_at = action.payload.updated_at;
        }
        if (state.draftStatus && state.draftStatus.id === action.payload.committed_from_draft_id) {
          state.draftStatus.status = "COMMITTED";
          state.draftStatus.is_locked = true;
          state.draftStatus.is_committed = true;
          state.draftStatus.updated_at = action.payload.updated_at;
        }
      })
      .addMatcher(complaintApi.endpoints.saveComplaintDraft.matchRejected, (state, action) => {
        state.isSavingComplaint = false;
        state.draftError = errorMessageFromPayload(action.payload, "Could not save complaint.");
      })
      .addMatcher(complaintApi.endpoints.developmentPatchComplaintDraft.matchFulfilled, (state, action) => {
        state.activeDraftId = action.payload.id;
        state.complaintDraft = action.payload;
        state.recentlyUpdatedFields = updatedFieldsFromPatch(action.meta.arg.originalArgs.body.patch);
        state.extractionStage = "complete";
        state.extractionProgress = 100;
      })
      .addMatcher(complaintApi.endpoints.developmentPatchComplaintDraft.matchRejected, (state, action) => {
        state.draftError = errorMessageFromPayload(action.payload, "Could not apply development patch.");
      });
  }
});

export const {
  clearDraftError,
  setActiveDraftId,
  setActiveIntelligenceTab,
  setComposerLocked,
  setDraftInfoMessage,
  setDraftSuccessMessage,
  setExtractionState,
  setIntelligenceDockExpanded
} = complaintSlice.actions;
