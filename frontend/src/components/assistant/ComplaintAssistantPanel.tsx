import { ShieldCheck } from "lucide-react";
import type { AssistantMessageState, ExtractionProgressState } from "../../types/complaintWorkspace";
import { StatusBadge } from "../common/StatusBadge";
import { AssistantComposer } from "./AssistantComposer";
import { AssistantConversation } from "./AssistantConversation";
import { ExtractionProgress } from "./ExtractionProgress";
import { UploadDropzone } from "./UploadDropzone";

interface ComplaintAssistantPanelProps {
  extraction: ExtractionProgressState;
  messages: AssistantMessageState[];
  onSendLocalMessage: (content: string) => void;
  isComposerLocked?: boolean;
}

export function ComplaintAssistantPanel({
  extraction,
  messages,
  onSendLocalMessage,
  isComposerLocked = false
}: ComplaintAssistantPanelProps) {
  return (
    <aside
      className="complaint-assistant-panel"
      data-testid="complaint-assistant-panel"
      aria-labelledby="assistant-panel-title"
    >
      <header className="assistant-header">
        <div>
          <h2 id="assistant-panel-title">AI Complaint Intake Assistant</h2>
        </div>
        <StatusBadge tone="purple">BETA</StatusBadge>
      </header>

      <div className="assistant-panel-content">
        <UploadDropzone />

        <div className="assistant-or" aria-hidden="true">
          OR
        </div>

        <button type="button" className="paste-button">
          Paste Complaint Text / Email
        </button>

        <div className="supported-file-panel" role="note">
          <ShieldCheck size={17} aria-hidden="true" />
          <div>
            <p>Supported formats: PDF, DOCX, TXT, EML</p>
            <p>Maximum file size: 10 MB</p>
          </div>
        </div>

        <ExtractionProgress extraction={extraction} />
        <AssistantConversation messages={messages} />
      </div>

      <AssistantComposer onSendLocalMessage={onSendLocalMessage} isLocked={isComposerLocked} />
    </aside>
  );
}
