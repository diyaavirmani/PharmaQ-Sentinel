import type { AssistantMessageState } from "../../types/complaintWorkspace";
import { AssistantMessage } from "./AssistantMessage";

interface AssistantConversationProps {
  messages: AssistantMessageState[];
}

export function AssistantConversation({ messages }: AssistantConversationProps) {
  return (
    <section
      className="assistant-conversation"
      data-testid="complaint-chat-messages"
      role="log"
      aria-live="polite"
      aria-label="Assistant conversation"
    >
      {messages.map((message) => (
        <AssistantMessage key={message.id} message={message} />
      ))}
    </section>
  );
}
