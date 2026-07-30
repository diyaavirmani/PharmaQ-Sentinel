import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { ComplaintFieldKey, ExtractionStage } from "../../types/complaintWorkspace";
import { complaintApi } from "./complaintApi";
import { serverFieldToUiField } from "./complaintMappers";
import type { ComplaintSliceState, IntelligenceTab } from "./complaintTypes";

const initialState: ComplaintSliceState = {
  activeDraftId: null,
  complaintDraft: null,
  draftStatus: null,
  isCreatingDraft: false,
  isLoadingDraft: false,
  isResettingDraft: false,
  draftError: null,
  draftInfoMessage: null,
  draftSuccessMessage: null,
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
        state.recentlyUpdatedFields = [];
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
        state.recentlyUpdatedFields = [];
        state.extractionStage = "idle";
        state.extractionProgress = 0;
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
