interface ConfirmationModalProps {
  title: string;
  message: string;
  isOpen: boolean;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationModal({
  title,
  message,
  isOpen,
  confirmLabel,
  cancelLabel,
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
        <div className="confirmation-actions">
          <button type="button" className="button button--secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button type="button" className="button button--primary" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
