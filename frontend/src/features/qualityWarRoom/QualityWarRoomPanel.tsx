import { useEffect, useMemo, useState } from "react";
import { BrainCircuit } from "lucide-react";
import {
  useGetQualityWarRoomRunQuery,
  useGetQualityWarRoomRunsQuery,
  useStartQualityWarRoomRunMutation
} from "../complaint/complaintApi";
import { AgentProgressTimeline } from "./AgentProgressTimeline";
import { AuditorChallengeCard } from "./AuditorChallengeCard";
import { ConsensusPanel } from "./ConsensusPanel";
import { PreviousRunsSelector } from "./PreviousRunsSelector";
import { SpecialistAgentCard } from "./SpecialistAgentCard";

export function QualityWarRoomPanel({ draftId }: { draftId: string | null }) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [startRun, startState] = useStartQualityWarRoomRunMutation();
  const runsQuery = useGetQualityWarRoomRunsQuery(draftId ?? "", { skip: !draftId });
  const selectedRun = selectedRunId ?? runsQuery.data?.[0]?.id ?? null;
  const runQuery = useGetQualityWarRoomRunQuery(
    { draftId: draftId ?? "", runId: selectedRun ?? "" },
    { skip: !draftId || !selectedRun }
  );

  useEffect(() => {
    if (!selectedRunId && runsQuery.data?.[0]?.id) {
      setSelectedRunId(runsQuery.data[0].id);
    }
  }, [runsQuery.data, selectedRunId]);

  const run = runQuery.data ?? runsQuery.data?.find((item) => item.id === selectedRun) ?? null;
  const specialistOutputs = useMemo(() => Object.values(run?.specialist_outputs_json ?? {}), [run]);

  function handleStart() {
    if (!draftId) {
      return;
    }
    void startRun({ draftId, createdBy: "Demo User" })
      .unwrap()
      .then((response) => {
        setSelectedRunId(response.run_id);
        void runsQuery.refetch();
      })
      .catch(() => undefined);
  }

  return (
    <div className="war-room-panel" data-testid="quality-war-room-panel">
      <div className="batch-impact-panel__header">
        <div>
          <span>DRAFT DECISION SUPPORT</span>
          <h3>AI Quality War Room</h3>
          <p>Bounded specialist review with auditor challenge and human approval required.</p>
        </div>
        <div className="batch-impact-panel__actions">
          <PreviousRunsSelector
            runs={runsQuery.data ?? []}
            selectedRunId={selectedRun}
            onSelectRun={setSelectedRunId}
          />
          <button
            type="button"
            className="button button--secondary"
            disabled={!draftId || startState.isLoading}
            onClick={handleStart}
          >
            <BrainCircuit size={16} aria-hidden="true" />
            {startState.isLoading ? "Running..." : "Run War Room"}
          </button>
        </div>
      </div>
      {startState.error || runQuery.error ? (
        <div className="complaint-panel-banner complaint-panel-banner--error">
          Quality War Room could not complete. Please retry.
        </div>
      ) : null}
      {!run ? (
        <div className="batch-impact-empty">Run the War Room after the draft has enough complaint context.</div>
      ) : (
        <div className="war-room-results">
          <AgentProgressTimeline events={run.events} />
          <div className="war-room-grid">
            {specialistOutputs.map((output) => <SpecialistAgentCard key={output.agent_name} output={output} />)}
          </div>
          <AuditorChallengeCard run={run} />
          <ConsensusPanel run={run} />
        </div>
      )}
    </div>
  );
}
