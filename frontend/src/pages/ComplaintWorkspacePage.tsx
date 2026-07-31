import { useEffect, useMemo, useRef, useState } from "react";
import { useAppDispatch, useAppSelector } from "../app/hooks";
import { ComplaintWorkspace } from "../components/complaint/ComplaintWorkspace";
import {
  useCreateComplaintDraftMutation,
  useGetComplaintAttachmentStatusQuery,
  useGetComplaintDraftQuery,
  useGetComplaintMessagesQuery,
  useGetComplaintEvidenceQuery,
  useGetComplaintFieldEvidenceQuery,
  useGetComplaintTimelineQuery,
  useGetComplaintDraftStatusQuery,
  useResetComplaintDraftMutation,
  useSaveComplaintDraftMutation,
  useSendComplaintMessageMutation,
  useUploadComplaintAttachmentMutation
} from "../features/complaint/complaintApi";
import {
  setActiveDraftId,
  setActiveIntelligenceTab,
  setDraftInfoMessage,
  setIntelligenceDockExpanded
} from "../features/complaint/complaintSlice";
import { mapDraftToWorkspaceState, createVisualRegressionState } from "../features/complaint/complaintMappers";
import {
  selectComplaintState,
  selectShouldEnableSaveComplaint
} from "../features/complaint/complaintSelectors";
import type { WorkspaceViewState } from "../types/complaintWorkspace";
import "../styles/workspace.css";

const activeDraftStorageKey = "pharmaq_active_draft_id";
const defaultCreatedBy = "Demo User";
const defaultChangeReason = "Initial complaint registration";

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
  const canSaveComplaint = useAppSelector(selectShouldEnableSaveComplaint);
  const [storedDraftId, setStoredDraftId] = useState<string | null>(() => getStoredDraftId());
  const createStartedRef = useRef(false);
  const [selectedEvidence, setSelectedEvidence] = useState<{ fieldName: string; label: string } | null>(null);
  const visualState = visualRegressionStateFromQuery();

  const [createDraft] = useCreateComplaintDraftMutation();
  const [resetDraft] = useResetComplaintDraftMutation();
  const [saveDraft] = useSaveComplaintDraftMutation();
  const [sendMessage] = useSendComplaintMessageMutation();
  const [uploadAttachment] = useUploadComplaintAttachmentMutation();
  const activeDraftId = complaintState.activeDraftId ?? storedDraftId;

  const getDraftQuery = useGetComplaintDraftQuery(storedDraftId ?? "", {
    skip: Boolean(visualState) || !storedDraftId
  });
  useGetComplaintDraftStatusQuery(activeDraftId ?? "", {
    skip: Boolean(visualState) || !activeDraftId
  });
  useGetComplaintAttachmentStatusQuery(
    {
      draftId: activeDraftId ?? "",
      attachmentId: complaintState.activeAttachmentId ?? ""
    },
    {
      skip: Boolean(visualState) || !activeDraftId || !complaintState.activeAttachmentId,
      pollingInterval:
        complaintState.extractionStage === "complete" || complaintState.extractionStage === "error"
          ? 0
          : 1500
    }
  );
  useGetComplaintMessagesQuery(activeDraftId ?? "", {
    skip: Boolean(visualState) || !activeDraftId
  });
  const evidenceQuery = useGetComplaintEvidenceQuery(activeDraftId ?? "", {
    skip: Boolean(visualState) || !activeDraftId
  });
  const fieldEvidenceQuery = useGetComplaintFieldEvidenceQuery(
    {
      draftId: activeDraftId ?? "",
      fieldName: selectedEvidence?.fieldName ?? ""
    },
    {
      skip: Boolean(visualState) || !activeDraftId || !selectedEvidence
    }
  );
  const timelineQuery = useGetComplaintTimelineQuery(activeDraftId ?? "", {
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
      messages: complaintState.assistantMessages,
      isLoading:
        (complaintState.isCreatingDraft || complaintState.isLoadingDraft) &&
        complaintState.complaintDraft === null,
      evidenceFieldNames: evidenceQuery.data?.items?.map((item) => item.field_name) ?? []
    });
  }, [complaintState, evidenceQuery.data, visualState]);

  function handleResetConfirmed() {
    if (!activeDraftId || visualState) {
      return;
    }

    void resetDraft(activeDraftId).unwrap();
  }

  function createIdempotencyKey() {
    if ("crypto" in window && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return `save-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }

  function handleSaveConfirmed(input: {
    reviewedBy: string;
    reviewMeaning: string;
    missingInformationAcknowledged: boolean;
  }) {
    if (!activeDraftId || visualState) {
      return;
    }

    void saveDraft({
      draftId: activeDraftId,
      body: {
        reviewed_by: input.reviewedBy,
        review_meaning: input.reviewMeaning,
        missing_information_acknowledged: input.missingInformationAcknowledged,
        change_reason: defaultChangeReason,
        idempotency_key: createIdempotencyKey()
      }
    }).unwrap();
  }

  function handleSendAssistantMessage(content: string) {
    if (!activeDraftId || visualState) {
      return;
    }

    void sendMessage({
      draftId: activeDraftId,
      body: {
        message: content,
        attachment_id: null
      }
    }).unwrap();
  }

  function handleUploadDocument(file: File) {
    if (!activeDraftId || visualState) {
      return;
    }

    void uploadAttachment({
      draftId: activeDraftId,
      file
    }).unwrap();
  }

  function handleAskFollowUpQuestions(questions: string[]) {
    if (!questions.length) {
      return;
    }
    handleSendAssistantMessage(`Please ask these follow-up questions: ${questions.join(" ")}`);
  }

  return (
    <main className="workspace-page" aria-label="PharmaQ Sentinel complaint workspace" data-font-family="Inter">
      <ComplaintWorkspace
        workspaceState={workspaceState}
        onResetConfirmed={handleResetConfirmed}
        onSaveConfirmed={handleSaveConfirmed}
        errorMessage={visualState ? null : complaintState.draftError}
        infoMessage={visualState ? null : complaintState.draftInfoMessage}
        successMessage={visualState ? null : complaintState.draftSuccessMessage}
        isResetting={complaintState.isResettingDraft}
        isSaving={complaintState.isSavingComplaint}
        canSave={visualState ? false : canSaveComplaint}
        committedComplaintId={complaintState.committedComplaint?.id ?? null}
        isComposerLocked={complaintState.isComposerLocked}
        onSendAssistantMessage={handleSendAssistantMessage}
        onUploadDocument={handleUploadDocument}
        selectedUploadFilename={complaintState.selectedUploadFilename}
        uploadError={complaintState.uploadError}
        onAskFollowUpQuestions={handleAskFollowUpQuestions}
        evidenceDetail={fieldEvidenceQuery.data}
        isEvidenceDetailLoading={fieldEvidenceQuery.isFetching}
        selectedEvidenceLabel={selectedEvidence?.label ?? null}
        onViewFieldEvidence={(fieldName, label) => setSelectedEvidence({ fieldName, label })}
        onCloseEvidenceDrawer={() => setSelectedEvidence(null)}
        timeline={timelineQuery.data?.items ?? []}
        activeDraftId={activeDraftId}
        isIntelligenceDockExpanded={complaintState.isIntelligenceDockExpanded}
        activeIntelligenceTab={complaintState.activeIntelligenceTab}
        onIntelligenceDockExpandedChange={(isExpanded) => dispatch(setIntelligenceDockExpanded(isExpanded))}
        onActiveIntelligenceTabChange={(tab) => dispatch(setActiveIntelligenceTab(tab))}
      />
    </main>
  );
}
