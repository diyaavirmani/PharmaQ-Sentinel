import clsx from "clsx";
import type { ExtractionProgressState } from "../../types/complaintWorkspace";

interface ExtractionProgressProps {
  extraction: ExtractionProgressState;
}

export function ExtractionProgress({ extraction }: ExtractionProgressProps) {
  return (
    <section
      className="extraction-progress"
      data-testid="complaint-extraction-progress"
      aria-labelledby="extraction-progress-title"
      aria-live="polite"
    >
      <div className="assistant-section-heading" id="extraction-progress-title">
        EXTRACTION PROGRESS
      </div>
      <div className="extraction-progress__body">
        <div className="extraction-progress__meta">
          <span className={clsx("progress-stage", `progress-stage--${extraction.stage}`)}>
            {extraction.stage}
          </span>
          <span>{extraction.percentage}%</span>
        </div>
        <div
          className="progress-bar"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={extraction.percentage}
          aria-label="Complaint extraction progress"
        >
          <span style={{ width: `${extraction.percentage}%` }} />
        </div>
        <p>{extraction.statusText}</p>
      </div>
    </section>
  );
}
