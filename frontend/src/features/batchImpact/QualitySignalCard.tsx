import clsx from "clsx";
import type { BatchImpactSignal } from "./batchImpactTypes";

interface QualitySignalCardProps {
  signal: BatchImpactSignal;
}

export function QualitySignalCard({ signal }: QualitySignalCardProps) {
  return (
    <article className={clsx("quality-signal-card", `quality-signal-card--${signal.level.toLowerCase()}`)}>
      <div>
        <span>{signal.category.replace(/_/g, " ")}</span>
        <strong>{signal.name}</strong>
      </div>
      <p>{signal.explanation}</p>
      <dl>
        <div>
          <dt>Confidence</dt>
          <dd>{signal.confidence}</dd>
        </div>
        <div>
          <dt>Assessment</dt>
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
