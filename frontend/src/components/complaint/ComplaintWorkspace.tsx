import { useEffect, useState } from "react";
import type { IntelligenceTab } from "../../features/complaint/complaintTypes";
import type { AssistantMessageState, ComplaintWorkspaceState } from "../../types/complaintWorkspace";
import { ComplaintAssistantPanel } from "../assistant/ComplaintAssistantPanel";
import { ConfirmationModal } from "../common/ConfirmationModal";
import { QualityIntelligenceDock } from "../intelligence/QualityIntelligenceDock";
import { ComplaintFormPanel } from "./ComplaintFormPanel";

interface ComplaintWorkspaceProps {
  workspaceState: ComplaintWorkspaceState;
  onResetConfirmed: () => void;
  errorMessage?: string | null;
  infoMessage?: string | null;
  successMessage?: string | null;
  isResetting?: boolean;
  isComposerLocked?: boolean;
  isIntelligenceDockExpanded: boolean;
  activeIntelligenceTab: IntelligenceTab;
  onIntelligenceDockExpandedChange: (isExpanded: boolean) => void;
  onActiveIntelligenceTabChange: (tab: IntelligenceTab) => void;
}

export function ComplaintWorkspace({
  workspaceState,
  onResetConfirmed,
  errorMessage = null,
  infoMessage = null,
  successMessage = null,
  isResetting = false,
  isComposerLocked = false,
  isIntelligenceDockExpanded,
  activeIntelligenceTab,
  onIntelligenceDockExpandedChange,
  onActiveIntelligenceTabChange
}: ComplaintWorkspaceProps) {
  const [messages, setMessages] = useState<AssistantMessageState[]>(workspaceState.messages);
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);

  useEffect(() => {
    if (messages.length === 0) {
      setMessages(workspaceState.messages);
    }
  }, [messages.length, workspaceState.messages]);

  function handleLocalMessage(content: string) {
    const trimmed = content.trim();
    if (!trimmed) {
      return;
    }

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: `local-user-message-${currentMessages.length + 1}`,
        role: "user",
        content: trimmed
      }
    ]);
  }

  function handleConfirmReset() {
    setIsResetModalOpen(false);
    onResetConfirmed();
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
          errorMessage={errorMessage}
          infoMessage={infoMessage}
          successMessage={successMessage}
          isResetting={isResetting}
        />
        <ComplaintAssistantPanel
          extraction={workspaceState.extraction}
          messages={messages}
          onSendLocalMessage={handleLocalMessage}
          isComposerLocked={isComposerLocked}
        />
      </div>
      <QualityIntelligenceDock
        visible={workspaceState.showQualityDock}
        isExpanded={isIntelligenceDockExpanded}
        activeTab={activeIntelligenceTab}
        onExpandedChange={onIntelligenceDockExpandedChange}
        onActiveTabChange={onActiveIntelligenceTabChange}
      />
      <ConfirmationModal
        title="Reset Complaint Draft"
        message="Extracted complaint values will be cleared. The draft ID, audit history, attachments and messages will be preserved."
        isOpen={isResetModalOpen}
        confirmLabel="Reset Form"
        cancelLabel="Cancel"
        onConfirm={handleConfirmReset}
        onCancel={() => setIsResetModalOpen(false)}
      />
    </div>
  );
}
