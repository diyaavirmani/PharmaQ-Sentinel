interface ComplaintFooterActionsProps {
  onReset: () => void;
  isResetting?: boolean;
}

export function ComplaintFooterActions({ onReset, isResetting = false }: ComplaintFooterActionsProps) {
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
        disabled
        aria-disabled="true"
      >
        Save Complaint
      </button>
    </footer>
  );
}
