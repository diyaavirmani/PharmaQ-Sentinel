export function EvidenceReferenceLink({ evidenceId }: { evidenceId: string }) {
  return <span className="evidence-reference-link">Evidence {evidenceId.slice(0, 8)}</span>;
}
