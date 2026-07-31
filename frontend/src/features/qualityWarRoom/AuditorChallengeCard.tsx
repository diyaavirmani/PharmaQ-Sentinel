import { ShieldAlert } from "lucide-react";
import type { QualityWarRoomRunResponse } from "./qualityWarRoomTypes";

export function AuditorChallengeCard({ run }: { run: QualityWarRoomRunResponse }) {
  const auditor = run.auditor_output_json;
  const items = [
    ...auditor.challenged_findings,
    ...auditor.rejected_claims,
    ...auditor.missing_evidence
  ];
  return (
    <article className="war-room-card war-room-card--auditor" data-testid="auditor-challenge-card">
      <header>
        <ShieldAlert size={16} aria-hidden="true" />
        <div>
          <h4>Compliance Auditor</h4>
          <span>{items.length} challenge or evidence notes</span>
        </div>
      </header>
      {items.length ? (
        <ul>
          {items.slice(0, 5).map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : (
        <p>No unsupported final claims were detected in the specialist summaries.</p>
      )}
    </article>
  );
}
