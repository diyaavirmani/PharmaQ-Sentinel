import type { ClipboardEvent } from "react";
import clsx from "clsx";
import { FileSearch } from "lucide-react";

const emptyFieldText = "Awaiting AI extraction...";

interface ReadOnlyFieldProps {
  id: string;
  label: string;
  value: string | null;
  unitSuffix?: string;
  multiline?: boolean;
  evidenceAvailable?: boolean;
  recentlyUpdated?: boolean;
  isLoading?: boolean;
  onViewEvidence?: () => void;
}

export function ReadOnlyField({
  id,
  label,
  value,
  unitSuffix,
  multiline = false,
  evidenceAvailable = false,
  recentlyUpdated = false,
  isLoading = false,
  onViewEvidence
}: ReadOnlyFieldProps) {
  const displayValue = value ?? emptyFieldText;
  const fieldClassName = clsx("read-only-field", {
    "read-only-field--empty": value === null,
    "read-only-field--multiline": multiline,
    "read-only-field--updated": recentlyUpdated,
    "read-only-field--loading": isLoading
  });

  const commonProps = {
    id,
    value: displayValue,
    readOnly: true,
    "aria-readonly": true,
    "aria-busy": isLoading,
    "data-readonly-field": "true",
    onPaste: (event: ClipboardEvent<HTMLInputElement | HTMLTextAreaElement>) => event.preventDefault(),
    className: "read-only-field__control"
  };

  return (
    <div className={fieldClassName}>
      <div className="read-only-field__label-row">
        <label htmlFor={id}>{label}</label>
        {value !== null && evidenceAvailable ? (
          <button
            type="button"
            className="evidence-icon-button"
            aria-label={`View evidence for ${label}`}
            onClick={onViewEvidence}
          >
            <FileSearch size={14} aria-hidden="true" />
          </button>
        ) : null}
      </div>
      <div className="read-only-field__input-wrap">
        {multiline ? <textarea {...commonProps} rows={5} /> : <input {...commonProps} type="text" />}
        {unitSuffix ? <span className="read-only-field__unit">{unitSuffix}</span> : null}
      </div>
      {recentlyUpdated ? <span className="read-only-field__updated">Updated by AI</span> : null}
    </div>
  );
}
