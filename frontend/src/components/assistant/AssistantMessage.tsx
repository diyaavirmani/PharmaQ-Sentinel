import { Bot, UserRound } from "lucide-react";
import type { AssistantMessageState } from "../../types/complaintWorkspace";

interface AssistantMessageProps {
  message: AssistantMessageState;
}

export function AssistantMessage({ message }: AssistantMessageProps) {
  const isAssistant = message.role === "assistant";

  return (
    <article className={`assistant-message assistant-message--${message.role}`} role="article" aria-label={`${message.role} message`}>
      <span className="assistant-message__icon" aria-hidden="true">
        {isAssistant ? <Bot size={15} /> : <UserRound size={15} />}
      </span>
      <p>{message.content}</p>
    </article>
  );
}
