import { SendHorizontal } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";

interface AssistantComposerProps {
  onSendLocalMessage: (content: string) => void;
  isLocked?: boolean;
}

export function AssistantComposer({ onSendLocalMessage, isLocked = false }: AssistantComposerProps) {
  const [message, setMessage] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLocked) {
      return;
    }
    onSendLocalMessage(message);
    setMessage("");
  }

  return (
    <form className="assistant-composer" onSubmit={handleSubmit}>
      <div className="assistant-composer__row">
        <label className="sr-only" htmlFor="assistant-composer-input">
          Ask me anything about this complaint...
        </label>
        <input
          id="assistant-composer-input"
          data-testid="complaint-chat-input"
          type="text"
          placeholder="Ask me anything about this complaint..."
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          disabled={isLocked}
        />
        <button
          type="submit"
          className="button button--icon button--primary"
          aria-label="Send assistant message"
          disabled={isLocked}
        >
          <SendHorizontal size={17} aria-hidden="true" />
        </button>
      </div>
      <p className="assistant-disclaimer">AI responses may contain errors. Please verify information.</p>
    </form>
  );
}
