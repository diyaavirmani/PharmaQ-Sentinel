import { CheckCircle2, CircleAlert } from "lucide-react";
import type { SpecialistOutput } from "./qualityWarRoomTypes";
import { EvidenceReferenceLink } from "./EvidenceReferenceLink";

export function SpecialistAgentCard({ output }: { output: SpecialistOutput }) {
  const isComplete = output.status === "COMPLETE";
  return (
    <article className="war-room-card" data-testid="specialist-agent-card">
      <header>
        {isComplete ? <CheckCircle2 size={16} aria-hidden="true" /> : <CircleAlert size={16} aria-hidden="true" />}
        <div>
          <h4>{output.agent_name}</h4>
          <span>{output.status} · {output.confidence} confidence</span>
        </div>
      </header>
      <ul>
        {output.concise_findings.slice(0, 3).map((finding) => (
          <li key={finding}>{finding}</li>
        ))}
      </ul>
      {output.evidence_ids.length ? (
        <div className="evidence-reference-row">
          {output.evidence_ids.slice(0, 3).map((id) => <EvidenceReferenceLink key={id} evidenceId={id} />)}
        </div>
      ) : null}
      <p>{output.limitations[0]}</p>
    </article>
  );
}
