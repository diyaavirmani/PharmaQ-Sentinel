import type { FieldEvidenceDetailResponse, FieldEvidenceResponse } from "../../features/complaint/complaintTypes";

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function statusLabel(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function EvidenceSource({ evidence }: { evidence: FieldEvidenceResponse }) {
  const source = evidence.source_attachment ?? evidence.source_message;
  const sourceLabel = evidence.source_attachment
    ? evidence.source_attachment.original_filename
    : evidence.source_message
      ? `${evidence.source_message.role.toLowerCase()} message`
      : "Source not linked";

  return (
    <div className="evidence-drawer__source">
      <span>{sourceLabel}</span>
      {evidence.page_number !== null ? <span>Page {evidence.page_number}</span> : null}
      {evidence.paragraph_index !== null ? <span>Paragraph {evidence.paragraph_index}</span> : null}
      {source ? <span>{source.created_at}</span> : null}
    </div>
  );
}

function EvidenceRecord({ evidence }: { evidence: FieldEvidenceResponse }) {
  return (
    <article className="evidence-record">
      <div className="evidence-record__header">
        <strong>{statusLabel(evidence.evidence_status)}</strong>
        <span>{evidence.confidence ? `${Math.round(Number(evidence.confidence) * 100)}% confidence` : "Confidence not provided"}</span>
      </div>
      <EvidenceSource evidence={evidence} />
      <p>{evidence.source_excerpt ?? "No source excerpt was captured."}</p>
      <dl>
        <div>
          <dt>Value</dt>
          <dd>{valueText(evidence.display_value)}</dd>
        </div>
        <div>
          <dt>Method</dt>
          <dd>{evidence.extraction_method ?? "Not provided"}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{evidence.actual_model ?? "Not provided"}</dd>
        </div>
      </dl>
    </article>
  );
}

export function EvidenceDrawerContent({
  label,
  detail,
  isLoading
}: {
  label: string;
  detail?: FieldEvidenceDetailResponse;
  isLoading: boolean;
}) {
  if (isLoading) {
    return <p className="evidence-drawer__empty">Loading evidence...</p>;
  }
  if (!detail) {
    return <p className="evidence-drawer__empty">No evidence is available for this field.</p>;
  }

  return (
    <div className="evidence-drawer">
      <div>
        <span className="evidence-drawer__eyebrow">{label}</span>
        <h3>{valueText(detail.current_value)}</h3>
      </div>
      {detail.conflicts.length ? (
        <div className="evidence-conflict" role="status">
          {detail.conflicts[0].description}
        </div>
      ) : null}
      {detail.current_active_evidence ? (
        <section>
          <h4>Current Active Evidence</h4>
          <EvidenceRecord evidence={detail.current_active_evidence} />
        </section>
      ) : null}
      <section>
        <h4>Previous Values</h4>
        <div className="evidence-history">
          {detail.evidence_history.map((evidence) => (
            <EvidenceRecord key={evidence.id} evidence={evidence} />
          ))}
        </div>
      </section>
    </div>
  );
}
