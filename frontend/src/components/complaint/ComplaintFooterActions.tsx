interface ComplaintFooterActionsProps {
  onReset: () => void;
  onSave: () => void;
  isResetting?: boolean;
  isSaving?: boolean;
  canSave?: boolean;
}

export function ComplaintFooterActions({
  onReset,
  onSave,
  isResetting = false,
  isSaving = false,
  canSave = false
}: ComplaintFooterActionsProps) {
  return (
    <footer className="complaint-footer-actions">
      <button
        type="button"
        className="button button--secondary"
        data-testid="complaint-reset-button"
        onClick={onReset}
        disabled={isResetting}
      >
        Reset Form
      </button>
      <button
        type="button"
        className="button button--primary"
        data-testid="complaint-save-button"
        disabled={!canSave || isSaving}
        aria-disabled={!canSave || isSaving}
        onClick={onSave}
      >
        Save Complaint
      </button>
    </footer>
  );
}
