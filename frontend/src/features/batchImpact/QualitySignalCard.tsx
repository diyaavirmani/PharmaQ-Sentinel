import clsx from "clsx";
import type { BatchImpactSignal } from "./batchImpactTypes";

interface QualitySignalCardProps {
  signal: BatchImpactSignal;
}

function percentText(value: string) {
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    return `${Math.round(numeric * 100)}%`;
  }
  return value;
}

export function QualitySignalCard({ signal }: QualitySignalCardProps) {
  return (
    <article className={clsx("quality-signal-card", `quality-signal-card--${signal.level.toLowerCase()}`)}>
      <div className="quality-signal-card__header">
        <span className={`priority-badge priority-badge--${signal.level.toLowerCase()}`}>{signal.level}</span>
        <strong>{signal.name}</strong>
      </div>
      <p>{signal.explanation}</p>
      <dl>
        <div>
          <dt>Evidence IDs</dt>
          <dd>{signal.evidence_record_ids.length ? signal.evidence_record_ids.join(", ") : "Not provided"}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{percentText(signal.confidence)}</dd>
        </div>
        <div>
          <dt>Action</dt>
          <dd>{signal.recommended_assessment}</dd>
        </div>
        <div>
          <dt>Limitation</dt>
          <dd>{signal.limitation}</dd>
        </div>
      </dl>
    </article>
  );
}
