import { useEffect, useMemo, useRef, useState } from "react";
import { useAppDispatch, useAppSelector } from "../app/hooks";
import { ComplaintWorkspace } from "../components/complaint/ComplaintWorkspace";
import {
  useCreateComplaintDraftMutation,
  useGetComplaintDraftQuery,
  useGetComplaintDraftStatusQuery,
  useResetComplaintDraftMutation
} from "../features/complaint/complaintApi";
import {
  setActiveDraftId,
  setActiveIntelligenceTab,
  setDraftInfoMessage,
  setIntelligenceDockExpanded
} from "../features/complaint/complaintSlice";
import { mapDraftToWorkspaceState, createVisualRegressionState } from "../features/complaint/complaintMappers";
import { selectComplaintState } from "../features/complaint/complaintSelectors";
import type { WorkspaceViewState } from "../types/complaintWorkspace";
import "../styles/workspace.css";

const activeDraftStorageKey = "pharmaq_active_draft_id";
const defaultCreatedBy = "Demo User";

function getStoredDraftId() {
  return window.sessionStorage.getItem(activeDraftStorageKey);
}

function isNotFoundError(error: unknown) {
  return typeof error === "object" && error !== null && "status" in error && error.status === 404;
}

function visualRegressionStateFromQuery(): WorkspaceViewState | null {
  const isEnabled =
    import.meta.env.MODE === "test" || import.meta.env.VITE_ENABLE_WORKSPACE_TEST_STATES === "true";
  if (!isEnabled) {
    return null;
  }

  const state = new URLSearchParams(window.location.search).get("state");
  if (state === "empty" || state === "extracting" || state === "populated" || state === "error" || state === "edited") {
    return state;
  }

  return null;
}

export function ComplaintWorkspacePage() {
  const dispatch = useAppDispatch();
  const complaintState = useAppSelector(selectComplaintState);
  const [storedDraftId, setStoredDraftId] = useState<string | null>(() => getStoredDraftId());
  const createStartedRef = useRef(false);
  const visualState = visualRegressionStateFromQuery();

  const [createDraft] = useCreateComplaintDraftMutation();
  const [resetDraft] = useResetComplaintDraftMutation();
  const activeDraftId = complaintState.activeDraftId ?? storedDraftId;

  const getDraftQuery = useGetComplaintDraftQuery(storedDraftId ?? "", {
    skip: Boolean(visualState) || !storedDraftId
  });
  useGetComplaintDraftStatusQuery(activeDraftId ?? "", {
    skip: Boolean(visualState) || !activeDraftId
  });

  useEffect(() => {
    if (storedDraftId) {
      dispatch(setActiveDraftId(storedDraftId));
    }
  }, [dispatch, storedDraftId]);

  useEffect(() => {
    if (visualState || storedDraftId || createStartedRef.current) {
      return;
    }

    createStartedRef.current = true;
    void createDraft({ created_by: defaultCreatedBy })
      .unwrap()
      .then((draft) => {
        window.sessionStorage.setItem(activeDraftStorageKey, draft.id);
        setStoredDraftId(draft.id);
      })
      .catch(() => undefined);
  }, [createDraft, storedDraftId, visualState]);

  useEffect(() => {
    if (!storedDraftId || !isNotFoundError(getDraftQuery.error)) {
      return;
    }

    window.sessionStorage.removeItem(activeDraftStorageKey);
    setStoredDraftId(null);
    dispatch(setActiveDraftId(null));
    dispatch(setDraftInfoMessage("Saved complaint draft was unavailable, so a new draft was created."));
  }, [dispatch, getDraftQuery.error, storedDraftId]);

  const workspaceState = useMemo(() => {
    if (visualState) {
      return createVisualRegressionState(visualState);
    }

    return mapDraftToWorkspaceState({
      draft: complaintState.complaintDraft,
      draftStatus: complaintState.draftStatus,
      recentlyUpdatedFields: complaintState.recentlyUpdatedFields,
      extractionStage: complaintState.extractionStage,
      extractionProgress: complaintState.extractionProgress,
      isLoading:
        (complaintState.isCreatingDraft || complaintState.isLoadingDraft) &&
        complaintState.complaintDraft === null
    });
  }, [complaintState, visualState]);

  function handleResetConfirmed() {
    if (!activeDraftId || visualState) {
      return;
    }

    void resetDraft(activeDraftId).unwrap();
  }

  return (
    <main className="workspace-page" aria-label="PharmaQ Sentinel complaint workspace" data-font-family="Inter">
      <ComplaintWorkspace
        workspaceState={workspaceState}
        onResetConfirmed={handleResetConfirmed}
        errorMessage={visualState ? null : complaintState.draftError}
        infoMessage={visualState ? null : complaintState.draftInfoMessage}
        successMessage={visualState ? null : complaintState.draftSuccessMessage}
        isResetting={complaintState.isResettingDraft}
        isComposerLocked={complaintState.isComposerLocked}
        isIntelligenceDockExpanded={complaintState.isIntelligenceDockExpanded}
        activeIntelligenceTab={complaintState.activeIntelligenceTab}
        onIntelligenceDockExpandedChange={(isExpanded) => dispatch(setIntelligenceDockExpanded(isExpanded))}
        onActiveIntelligenceTabChange={(tab) => dispatch(setActiveIntelligenceTab(tab))}
      />
    </main>
  );
}
