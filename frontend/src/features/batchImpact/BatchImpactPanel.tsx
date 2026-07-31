import { useRef, useState } from "react";
import { Network, Play, ShieldCheck } from "lucide-react";
import {
  useRunBatchImpactMutation,
  useSimulateBatchImpactMutation
} from "../complaint/complaintApi";
import type { BatchImpactEdge, BatchImpactNode, ContainmentSimulationRequest } from "./batchImpactTypes";
import { BatchImpactGraph } from "./BatchImpactGraph";
import { BatchImpactMetrics } from "./BatchImpactMetrics";
import { ContainmentSimulatorModal } from "./ContainmentSimulatorModal";
import { NodeDetailDrawer } from "./NodeDetailDrawer";
import { QualitySignalCard } from "./QualitySignalCard";

interface BatchImpactPanelProps {
  draftId: string | null;
  batchNumber?: string | null;
}

function errorText(error: unknown) {
  if (typeof error === "object" && error !== null && "data" in error) {
    const data = (error as { data?: unknown }).data;
    if (typeof data === "object" && data !== null && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
  }
  return "Batch Intelligence could not complete. Please retry.";
}

export function BatchImpactPanel({ draftId, batchNumber }: BatchImpactPanelProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [runBatchImpact, runState] = useRunBatchImpactMutation();
  const [simulateBatchImpact, simulateState] = useSimulateBatchImpactMutation();
  const [selectedNode, setSelectedNode] = useState<BatchImpactNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<BatchImpactEdge | null>(null);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);
  const result = runState.data ?? null;
  const canRun = Boolean(draftId && batchNumber);

  function handleRunAnalysis() {
    if (!draftId) {
      return;
    }
    void runBatchImpact({ draftId, createdBy: "Demo User" })
      .unwrap()
      .then(() => {
        panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(() => undefined);
  }

  function handleSimulate(body: ContainmentSimulationRequest) {
    if (!draftId) {
      return;
    }
    void simulateBatchImpact({ draftId, body }).unwrap().catch(() => undefined);
  }

  return (
    <div className="batch-impact-panel" data-testid="batch-impact-panel" ref={panelRef}>
      <div className="batch-impact-panel__header">
        <div>
          <span>DEMONSTRATION DATA</span>
          <h3>Batch Blast-Radius Digital Twin</h3>
          <p>Connected records for review. Relationships do not establish final quality impact.</p>
        </div>
        <div className="batch-impact-panel__actions">
          <button
            type="button"
            className="button button--secondary"
            disabled={!canRun || runState.isLoading}
            onClick={handleRunAnalysis}
          >
            <Network size={16} aria-hidden="true" />
            {runState.isLoading ? "Running..." : "Run Analysis"}
          </button>
          <button
            type="button"
            className="button button--primary"
            disabled={!result}
            onClick={() => setIsSimulatorOpen(true)}
          >
            <ShieldCheck size={16} aria-hidden="true" />
            Simulate Scope
          </button>
        </div>
      </div>

      {!batchNumber ? (
        <div className="batch-impact-empty">
          <Play size={16} aria-hidden="true" />
          Add a batch number through the assistant before running Batch Intelligence.
        </div>
      ) : null}

      {runState.error ? <div className="complaint-panel-banner complaint-panel-banner--error">{errorText(runState.error)}</div> : null}
      {runState.isLoading ? <div className="batch-impact-loading">Building connected batch graph...</div> : null}

      {result ? (
        <div className="batch-impact-results">
          <BatchImpactMetrics summary={result.impact_summary} />
          <BatchImpactGraph
            nodes={result.nodes}
            edges={result.edges}
            onNodeSelected={setSelectedNode}
            onEdgeSelected={setSelectedEdge}
          />
          {selectedEdge ? (
            <div className="batch-impact-edge-detail" data-testid="batch-impact-edge-detail">
              <strong>Why is this connected?</strong>
              <p>{selectedEdge.why_connected}</p>
              <span>{selectedEdge.limitation}</span>
            </div>
          ) : null}
          <div className="batch-impact-columns">
            <section>
              <h4>Quality Signals</h4>
              <div className="quality-signal-list">
                {result.signals.map((signal) => (
                  <QualitySignalCard key={`${signal.category}-${signal.name}`} signal={signal} />
                ))}
              </div>
            </section>
            <section>
              <h4>Recommended Assessments</h4>
              <ul className="recommended-assessments">
                {result.recommended_assessments.map((assessment) => (
                  <li key={assessment.title}>
                    <strong>{assessment.title}</strong>
                    <p>{assessment.rationale}</p>
                    <span>{assessment.limitation}</span>
                  </li>
                ))}
              </ul>
              <div className="batch-impact-limitations">
                <strong>Limitations</strong>
                <ul>
                  {result.limitations.map((limitation) => (
                    <li key={limitation}>{limitation}</li>
                  ))}
                </ul>
              </div>
            </section>
          </div>
        </div>
      ) : null}

      <NodeDetailDrawer node={selectedNode} onClose={() => setSelectedNode(null)} />
      <ContainmentSimulatorModal
        isOpen={isSimulatorOpen}
        isSimulating={simulateState.isLoading}
        result={simulateState.data ?? null}
        onCancel={() => setIsSimulatorOpen(false)}
        onSimulate={handleSimulate}
      />
    </div>
  );
}
