import { EvidenceReferenceLink } from "./EvidenceReferenceLink";
import type { QualityWarRoomRunResponse } from "./qualityWarRoomTypes";

export function ConsensusPanel({ run }: { run: QualityWarRoomRunResponse }) {
  const consensus = run.consensus_json;
  return (
    <section className="consensus-panel" data-testid="consensus-panel">
      <div className="batch-impact-metrics">
        <div>
          <span>Suggested Severity</span>
          <strong>{consensus.suggested_severity}</strong>
        </div>
        <div>
          <span>Suggested Priority</span>
          <strong>{consensus.suggested_priority}</strong>
        </div>
        <div>
          <span>Human Approval</span>
          <strong>{consensus.human_approval_required ? "Required" : "Not required"}</strong>
        </div>
      </div>
      <div className="war-room-grid">
        <article className="war-room-card">
          <h4>Investigation Priorities</h4>
          <ul>{consensus.investigation_priorities.slice(0, 5).map((item) => <li key={item}>{item}</li>)}</ul>
        </article>
        <article className="war-room-card">
          <h4>Potential Root-Cause Hypotheses</h4>
          <ul>{consensus.root_cause_hypotheses.slice(0, 5).map((item) => <li key={item}>{item}</li>)}</ul>
        </article>
        <article className="war-room-card">
          <h4>Disagreements & Rejected Claims</h4>
          <ul>
            {[...consensus.agent_disagreements, ...consensus.rejected_unsupported_claims].slice(0, 5).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="war-room-card">
          <h4>Limitations</h4>
          <ul>{consensus.limitations.slice(0, 4).map((item) => <li key={item}>{item}</li>)}</ul>
        </article>
      </div>
      {consensus.evidence_ids.length ? (
        <div className="evidence-reference-row">
          {consensus.evidence_ids.map((id) => <EvidenceReferenceLink key={id} evidenceId={id} />)}
        </div>
      ) : null}
    </section>
  );
}
