import { SearchCheck } from "lucide-react";
import {
  useRunDuplicateAnalysisMutation,
  useRunInvestigationPlaybookMutation
} from "../complaint/complaintApi";
import type { DuplicateAnalysisResult, InvestigationPlaybookResult, PlaybookStep } from "./investigationSupportTypes";

interface InvestigationSupportPanelProps {
  draftId: string | null;
  duplicateAnalysis: DuplicateAnalysisResult | null;
  playbook: InvestigationPlaybookResult | null;
  onDuplicateAnalysisComplete: (result: DuplicateAnalysisResult) => void;
  onPlaybookComplete: (result: InvestigationPlaybookResult) => void;
}

function StepList({ title, steps }: { title: string; steps: PlaybookStep[] }) {
  return (
    <article className="war-room-card">
      <h4>{title}</h4>
      {steps.length ? (
        <ul>
          {steps.map((step) => (
            <li key={step.id}>
              <strong>{step.title}</strong>
              <span>{step.rationale}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p>Run investigation support to populate this section.</p>
      )}
    </article>
  );
}

export function InvestigationSupportPanel({
  draftId,
  duplicateAnalysis,
  playbook,
  onDuplicateAnalysisComplete,
  onPlaybookComplete
}: InvestigationSupportPanelProps) {
  const [runDuplicateAnalysis, duplicateState] = useRunDuplicateAnalysisMutation();
  const [runPlaybook, playbookState] = useRunInvestigationPlaybookMutation();

  function handleRun() {
    if (!draftId) {
      return;
    }
    void runDuplicateAnalysis({ draftId, createdBy: "Demo User" })
      .unwrap()
      .then(onDuplicateAnalysisComplete)
      .catch(() => undefined);
    void runPlaybook({ draftId, createdBy: "Demo User" })
      .unwrap()
      .then(onPlaybookComplete)
      .catch(() => undefined);
  }

  const isLoading = duplicateState.isLoading || playbookState.isLoading;
  const candidates = duplicateAnalysis?.candidates ?? [];
  const recurrence = duplicateAnalysis?.recurrence_signals ?? [];
  const capaBuckets = Object.entries(playbook?.CAPA_considerations ?? {});

  return (
    <div className="investigation-support-panel" data-testid="investigation-support-panel">
      <div className="batch-impact-panel__header">
        <div>
          <span>DEVELOPMENT DECISION SUPPORT</span>
          <h3>Investigation Support</h3>
          <p>Duplicate, recurrence and playbook suggestions remain reviewer-controlled.</p>
        </div>
        <button
          type="button"
          className="button button--secondary"
          disabled={!draftId || isLoading}
          onClick={handleRun}
        >
          <SearchCheck size={16} aria-hidden="true" />
          {isLoading ? "Running..." : "Run Support"}
        </button>
      </div>
      {duplicateState.error || playbookState.error ? (
        <div className="complaint-panel-banner complaint-panel-banner--error">
          Investigation Support could not complete. Please retry.
        </div>
      ) : null}
      <div className="war-room-grid">
        <article className="war-room-card" data-testid="duplicate-details-table">
          <h4>Potential Duplicates</h4>
          {candidates.length ? (
            <table className="duplicate-table">
              <thead>
                <tr>
                  <th>Complaint</th>
                  <th>Classification</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {candidates.slice(0, 6).map((candidate) => (
                  <tr key={candidate.candidate_complaint_id}>
                    <td>{candidate.complaint_number}</td>
                    <td>{candidate.classification.replace(/_/g, " ")}</td>
                    <td>{candidate.total_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No duplicate candidates have been generated for this draft.</p>
          )}
        </article>
        <article className="war-room-card">
          <h4>Recurrence Signals</h4>
          {recurrence.length ? (
            <ul>{recurrence.map((signal) => <li key={signal.signal_type}>{signal.description}</li>)}</ul>
          ) : (
            <p>No recurrence signals generated yet.</p>
          )}
        </article>
      </div>
      <div className="war-room-grid">
        <StepList title="Immediate Containment" steps={playbook?.immediate_containment ?? []} />
        <StepList title="Investigation Checklist" steps={playbook?.investigation_checklist ?? []} />
        <StepList title="Root-Cause Hypotheses" steps={playbook?.root_cause_hypotheses ?? []} />
        <article className="war-room-card">
          <h4>CAPA Considerations</h4>
          {capaBuckets.length ? (
            capaBuckets.map(([bucket, steps]) => (
              <div key={bucket} className="capa-bucket">
                <strong>{bucket.replace(/_/g, " ")}</strong>
                <ul>{steps.map((step) => <li key={step.id}>{step.title}</li>)}</ul>
              </div>
            ))
          ) : (
            <p>No CAPA considerations have been generated. This panel never creates official CAPA records.</p>
          )}
        </article>
      </div>
    </div>
  );
}
