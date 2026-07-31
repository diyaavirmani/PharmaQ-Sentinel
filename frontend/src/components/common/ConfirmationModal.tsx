import type { ReactNode } from "react";

interface ConfirmationModalProps {
  title: string;
  message: string;
  isOpen: boolean;
  confirmLabel: string;
  cancelLabel: string;
  children?: ReactNode;
  isConfirmDisabled?: boolean;
  isProcessing?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationModal({
  title,
  message,
  isOpen,
  confirmLabel,
  cancelLabel,
  children,
  isConfirmDisabled = false,
  isProcessing = false,
  onConfirm,
  onCancel
}: ConfirmationModalProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="overlay-backdrop" role="presentation">
      <section className="confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="confirmation-title">
        <h2 id="confirmation-title">{title}</h2>
        <p>{message}</p>
        {children}
        <div className="confirmation-actions">
          <button type="button" className="button button--secondary" onClick={onCancel} disabled={isProcessing}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className="button button--primary"
            onClick={onConfirm}
            disabled={isConfirmDisabled || isProcessing}
          >
            {isProcessing ? "Saving..." : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
