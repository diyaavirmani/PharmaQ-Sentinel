import { useEffect, useState } from "react";
import type { FieldEvidenceDetailResponse, IntelligenceTab, TimelineEntryResponse } from "../../features/complaint/complaintTypes";
import type { ComplaintWorkspaceState } from "../../types/complaintWorkspace";
import { ComplaintAssistantPanel } from "../assistant/ComplaintAssistantPanel";
import { ConfirmationModal } from "../common/ConfirmationModal";
import { OverlayDrawer } from "../common/OverlayDrawer";
import { QualityIntelligenceDock } from "../intelligence/QualityIntelligenceDock";
import { ComplaintFormPanel } from "./ComplaintFormPanel";
import { EvidenceDrawerContent } from "./EvidenceDrawerContent";

interface ComplaintWorkspaceProps {
  workspaceState: ComplaintWorkspaceState;
  onResetConfirmed: () => void;
  onSaveConfirmed: (input: {
    reviewedBy: string;
    reviewMeaning: string;
    missingInformationAcknowledged: boolean;
  }) => void;
  errorMessage?: string | null;
  infoMessage?: string | null;
  successMessage?: string | null;
  isResetting?: boolean;
  isSaving?: boolean;
  canSave?: boolean;
  committedComplaintId?: string | null;
  isComposerLocked?: boolean;
  onSendAssistantMessage: (content: string) => void;
  onUploadDocument: (file: File) => void;
  selectedUploadFilename?: string | null;
  uploadError?: string | null;
  onAskFollowUpQuestions?: (questions: string[]) => void;
  evidenceDetail?: FieldEvidenceDetailResponse;
  isEvidenceDetailLoading?: boolean;
  onViewFieldEvidence?: (fieldName: string, label: string) => void;
  onCloseEvidenceDrawer?: () => void;
  selectedEvidenceLabel?: string | null;
  timeline?: TimelineEntryResponse[];
  activeDraftId?: string | null;
  isIntelligenceDockExpanded: boolean;
  activeIntelligenceTab: IntelligenceTab;
  onIntelligenceDockExpandedChange: (isExpanded: boolean) => void;
  onActiveIntelligenceTabChange: (tab: IntelligenceTab) => void;
}

export function ComplaintWorkspace({
  workspaceState,
  onResetConfirmed,
  onSaveConfirmed,
  errorMessage = null,
  infoMessage = null,
  successMessage = null,
  isResetting = false,
  isSaving = false,
  canSave = false,
  committedComplaintId = null,
  isComposerLocked = false,
  onSendAssistantMessage,
  onUploadDocument,
  selectedUploadFilename = null,
  uploadError = null,
  onAskFollowUpQuestions,
  evidenceDetail,
  isEvidenceDetailLoading = false,
  onViewFieldEvidence,
  onCloseEvidenceDrawer,
  selectedEvidenceLabel = null,
  timeline,
  activeDraftId = null,
  isIntelligenceDockExpanded,
  activeIntelligenceTab,
  onIntelligenceDockExpandedChange,
  onActiveIntelligenceTabChange
}: ComplaintWorkspaceProps) {
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [reviewedBy, setReviewedBy] = useState("Demo QA User");
  const [reviewMeaning, setReviewMeaning] = useState(
    "I reviewed the complaint information and AI-suggested assessment."
  );
  const [missingInformationAcknowledged, setMissingInformationAcknowledged] = useState(false);
  const missingInformation = workspaceState.draft.completeness?.missingItems ?? [];
  const requiresMissingAck = missingInformation.length > 0;

  useEffect(() => {
    if (committedComplaintId) {
      setIsSaveModalOpen(false);
    }
  }, [committedComplaintId]);

  function handleLocalMessage(content: string) {
    const trimmed = content.trim();
    if (!trimmed) {
      return;
    }
    onSendAssistantMessage(trimmed);
  }

  function handleConfirmReset() {
    setIsResetModalOpen(false);
    onResetConfirmed();
  }

  function handleConfirmSave() {
    onSaveConfirmed({
      reviewedBy,
      reviewMeaning,
      missingInformationAcknowledged: !requiresMissingAck || missingInformationAcknowledged
    });
  }

  return (
    <div className="workspace-shell">
      <div
        className="complaint-workspace complaint-workspace-grid"
        data-testid="complaint-workspace"
        data-responsive="stack-below-900"
        data-column-count="2"
      >
        <ComplaintFormPanel
          draft={workspaceState.draft}
          onReset={() => setIsResetModalOpen(true)}
          onSave={() => setIsSaveModalOpen(true)}
          errorMessage={errorMessage}
          infoMessage={infoMessage}
          successMessage={successMessage}
          isResetting={isResetting}
          isSaving={isSaving}
          canSave={canSave}
          committedComplaintId={committedComplaintId}
          onAskFollowUpQuestions={onAskFollowUpQuestions}
          onViewFieldEvidence={onViewFieldEvidence}
        />
        <ComplaintAssistantPanel
          extraction={workspaceState.extraction}
          messages={workspaceState.messages}
          onSendLocalMessage={handleLocalMessage}
          onUploadDocument={onUploadDocument}
          isComposerLocked={isComposerLocked}
          selectedUploadFilename={selectedUploadFilename}
          uploadError={uploadError}
        />
      </div>
      <QualityIntelligenceDock
        visible={workspaceState.showQualityDock}
        isExpanded={isIntelligenceDockExpanded}
        activeTab={activeIntelligenceTab}
        draftId={activeDraftId}
        batchNumber={workspaceState.draft.fields.batchLotNumber.value}
        timeline={timeline}
        onExpandedChange={onIntelligenceDockExpandedChange}
        onActiveTabChange={onActiveIntelligenceTabChange}
      />
      <OverlayDrawer
        title={selectedEvidenceLabel ? `Evidence: ${selectedEvidenceLabel}` : "Evidence"}
        isOpen={Boolean(selectedEvidenceLabel)}
        onClose={() => onCloseEvidenceDrawer?.()}
      >
        <EvidenceDrawerContent
          label={selectedEvidenceLabel ?? "Evidence"}
          detail={evidenceDetail}
          isLoading={isEvidenceDetailLoading}
        />
      </OverlayDrawer>
      <ConfirmationModal
        title="Reset Complaint Draft"
        message="Extracted complaint values will be cleared. The draft ID, audit history, attachments and messages will be preserved."
        isOpen={isResetModalOpen}
        confirmLabel="Reset Form"
        cancelLabel="Cancel"
        onConfirm={handleConfirmReset}
        onCancel={() => setIsResetModalOpen(false)}
      />
      <ConfirmationModal
        title="Save Complaint"
        message="Save this reviewed demonstration complaint record to the QMS ledger."
        isOpen={isSaveModalOpen}
        confirmLabel="Save Complaint"
        cancelLabel="Cancel"
        isProcessing={isSaving}
        isConfirmDisabled={
          !reviewedBy.trim() ||
          !reviewMeaning.trim() ||
          (requiresMissingAck && !missingInformationAcknowledged)
        }
        onConfirm={handleConfirmSave}
        onCancel={() => setIsSaveModalOpen(false)}
      >
        <div className="save-review-modal">
          <dl className="save-review-summary">
            <div>
              <dt>Product</dt>
              <dd>{workspaceState.draft.fields.productName.value ?? "Not provided"}</dd>
            </div>
            <div>
              <dt>Batch</dt>
              <dd>{workspaceState.draft.fields.batchLotNumber.value ?? "Not provided"}</dd>
            </div>
            <div>
              <dt>Complaint</dt>
              <dd>{workspaceState.draft.fields.complaintType.value ?? "Not provided"}</dd>
            </div>
            <div>
              <dt>Suggested Severity</dt>
              <dd>{workspaceState.draft.fields.initialSeverity.value ?? "Not provided"}</dd>
            </div>
          </dl>
          <div className="save-review-field">
            <label htmlFor="save-reviewed-by">Reviewer</label>
            <input
              id="save-reviewed-by"
              type="text"
              value={reviewedBy}
              onChange={(event) => setReviewedBy(event.target.value)}
            />
          </div>
          <div className="save-review-field">
            <label htmlFor="save-review-meaning">Review Meaning</label>
            <textarea
              id="save-review-meaning"
              rows={3}
              value={reviewMeaning}
              onChange={(event) => setReviewMeaning(event.target.value)}
            />
          </div>
          <div className="save-review-warning">
            <strong>Missing Information</strong>
            {missingInformation.length ? (
              <ul>
                {missingInformation.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>No missing information is currently listed.</p>
            )}
          </div>
          <div className="save-review-warning">
            <strong>Unresolved Warnings</strong>
            <p>AI-suggested assessment remains a draft input requiring human review.</p>
          </div>
          {requiresMissingAck ? (
            <label className="save-review-checkbox">
              <input
                type="checkbox"
                checked={missingInformationAcknowledged}
                onChange={(event) => setMissingInformationAcknowledged(event.target.checked)}
              />
              I acknowledge the listed non-critical missing information.
            </label>
          ) : null}
        </div>
      </ConfirmationModal>
    </div>
  );
}
