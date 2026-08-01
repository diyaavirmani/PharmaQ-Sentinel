import { useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { Network, Play, ShieldCheck } from "lucide-react";
import {
  useRunBatchImpactMutation,
  useSimulateBatchImpactMutation
} from "../complaint/complaintApi";
import type {
  BatchImpactEdge,
  BatchImpactNode,
  BatchImpactResponse,
  BatchImpactSignal,
  ContainmentSimulationRequest,
  RecommendedAssessment
} from "./batchImpactTypes";
import { BatchImpactGraph } from "./BatchImpactGraph";
import { BatchImpactMetrics, formatQuantity } from "./BatchImpactMetrics";
import { ContainmentSimulatorModal } from "./ContainmentSimulatorModal";
import { NodeDetailDrawer } from "./NodeDetailDrawer";
import { QualitySignalCard } from "./QualitySignalCard";

type BatchImpactTab = "overview" | "map" | "details";

interface BatchImpactPanelProps {
  draftId: string | null;
  batchNumber?: string | null;
}

interface ReviewRow {
  id: string;
  priority: BatchImpactSignal["level"];
  area: string;
  finding: string;
  connectedRecords: string[];
  whyItMatters: string;
  recommendedReview: string;
  confidence: string;
  limitation: string;
  evidenceRecordIds: string[];
}

const priorityRank: Record<BatchImpactSignal["level"], number> = {
  HIGH: 0,
  ELEVATED: 1,
  WATCH: 2,
  INFO: 3
};

const areaByCategory: Record<string, string> = {
  related_batch: "Related batches",
  batch_relationship: "Related batches",
  material: "Materials and packaging",
  packaging: "Materials and packaging",
  equipment: "Equipment and production line",
  line: "Equipment and production line",
  quality: "Deviations and CAPAs",
  quality_event: "Deviations and CAPAs",
  complaint_history: "Complaint history",
  recurrence: "Complaint history",
  distribution: "Distribution and inventory",
  inventory: "Distribution and inventory",
  supplier: "Suppliers",
  manufacturing_window: "Manufacturing time window"
};

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

function priorityLabel(priority: string | null | undefined) {
  return (priority || "INFO").replace(/_/g, " ").toUpperCase();
}

function percentText(value: string | null | undefined) {
  if (!value) {
    return "Not provided";
  }
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    return `${Math.round(numeric * 100)}%`;
  }
  return value;
}

function normaliseCategory(category: string) {
  return areaByCategory[category] ?? areaByCategory[category.toLowerCase()] ?? category.replace(/_/g, " ");
}

function nodeRecordLabel(node: BatchImpactNode | undefined) {
  if (!node) {
    return null;
  }
  return node.label || node.evidence_record_id || node.id;
}

function connectedRecordLabels(signal: BatchImpactSignal, nodeByEvidenceId: Map<string, BatchImpactNode>) {
  const labels = signal.evidence_record_ids
    .map((id) => nodeRecordLabel(nodeByEvidenceId.get(id)) ?? id)
    .filter(Boolean);
  return labels.length ? Array.from(new Set(labels)) : ["Evidence listed in details"];
}

function buildReviewRows(result: BatchImpactResponse): ReviewRow[] {
  const nodeByEvidenceId = new Map(
    result.nodes
      .filter((node) => node.evidence_record_id)
      .map((node) => [node.evidence_record_id as string, node])
  );
  return [...result.signals]
    .sort((left, right) => priorityRank[left.level] - priorityRank[right.level] || left.name.localeCompare(right.name))
    .map((signal) => ({
      id: `${signal.category}-${signal.name}`,
      priority: signal.level,
      area: normaliseCategory(signal.category),
      finding: signal.name,
      connectedRecords: connectedRecordLabels(signal, nodeByEvidenceId),
      whyItMatters: signal.explanation,
      recommendedReview: signal.recommended_assessment,
      confidence: percentText(signal.confidence),
      limitation: signal.limitation,
      evidenceRecordIds: signal.evidence_record_ids
    }));
}

function globalLimitation(result: BatchImpactResponse) {
  return (
    result.limitations.find((limitation) => /causation|quality impact|root cause/i.test(limitation)) ??
    result.impact_summary.data_limitations.find((limitation) => /causation|quality impact|root cause/i.test(limitation)) ??
    "Connected records indicate assessment scope; they do not establish final quality impact or root cause."
  );
}

function executiveSummary(result: BatchImpactResponse) {
  const summary = result.impact_summary;
  const related = summary.related_batches.length;
  const deviationText = `${summary.open_deviations} open deviation${summary.open_deviations === 1 ? "" : "s"}`;
  const capaText = `${summary.linked_capas} linked CAPA${summary.linked_capas === 1 ? "" : "s"}`;
  return `${related} related batch${related === 1 ? "" : "es"} share material, packaging, or equipment connections. ${deviationText} and ${capaText} require review. ${formatQuantity(summary.distributed_quantity)} were distributed and ${formatQuantity(summary.remaining_inventory)} remain in inventory.`;
}

function evidenceButtonLabel(action: RecommendedAssessment) {
  return action.evidence_record_ids.length ? `View evidence for ${action.title}` : undefined;
}

export function BatchImpactPanel({ draftId, batchNumber }: BatchImpactPanelProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [runBatchImpact, runState] = useRunBatchImpactMutation();
  const [simulateBatchImpact, simulateState] = useSimulateBatchImpactMutation();
  const [selectedNode, setSelectedNode] = useState<BatchImpactNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<BatchImpactEdge | null>(null);
  const [selectedReviewRow, setSelectedReviewRow] = useState<ReviewRow | null>(null);
  const [selectedAssessment, setSelectedAssessment] = useState<RecommendedAssessment | null>(null);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<BatchImpactTab>("overview");
  const [showAllRows, setShowAllRows] = useState(false);
  const [showAllActions, setShowAllActions] = useState(false);
  const result = runState.data ?? null;
  const canRun = Boolean(draftId && batchNumber);
  const reviewRows = useMemo(() => (result ? buildReviewRows(result) : []), [result]);
  const visibleRows = showAllRows ? reviewRows : reviewRows.slice(0, 6);
  const topActions = result ? result.recommended_assessments.slice(0, showAllActions ? undefined : 3) : [];
  const limitation = result ? globalLimitation(result) : null;

  function handleRunAnalysis() {
    if (!draftId) {
      return;
    }
    void runBatchImpact({ draftId, createdBy: "Demo User" })
      .unwrap()
      .then(() => {
        setActiveTab("overview");
        setShowAllRows(false);
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

  function openReviewDetails(row: ReviewRow) {
    setSelectedReviewRow(row);
  }

  function closeReviewDetails() {
    setSelectedReviewRow(null);
    setSelectedAssessment(null);
  }

  return (
    <div className="batch-impact-panel" data-testid="batch-impact-panel" ref={panelRef}>
      <div className="batch-impact-panel__header">
        <div className="batch-impact-panel__title">
          <span>DEMONSTRATION DATA</span>
          <h3>Batch Blast-Radius Digital Twin</h3>
          <p>Connected records requiring QA assessment</p>
          <div className="batch-impact-header-facts" aria-label="Batch Intelligence summary facts">
            <span>Primary batch: {result?.impact_summary.primary_batch ?? batchNumber ?? "Not provided"}</span>
            <span className={clsx("priority-badge", `priority-badge--${priorityLabel(result?.impact_summary.overall_investigation_priority).toLowerCase()}`)}>
              Review priority: {priorityLabel(result?.impact_summary.overall_investigation_priority)}
            </span>
          </div>
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
          <section className="batch-impact-executive-summary" aria-label="Batch Intelligence executive summary">
            <span>{priorityLabel(result.impact_summary.overall_investigation_priority)} REVIEW PRIORITY</span>
            <p>{executiveSummary(result)}</p>
            <small>{limitation}</small>
          </section>

          <div className="batch-impact-internal-tabs" role="tablist" aria-label="Batch Intelligence views">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "overview"}
              aria-controls="batch-impact-overview"
              id="batch-impact-tab-overview"
              onClick={() => setActiveTab("overview")}
            >
              Overview
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "map"}
              aria-controls="batch-impact-map"
              id="batch-impact-tab-map"
              onClick={() => setActiveTab("map")}
            >
              Relationship Map
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "details"}
              aria-controls="batch-impact-details"
              id="batch-impact-tab-details"
              onClick={() => setActiveTab("details")}
            >
              Details & Limitations
            </button>
          </div>

          {activeTab === "overview" ? (
            <section
              id="batch-impact-overview"
              role="tabpanel"
              aria-labelledby="batch-impact-tab-overview"
              className="batch-impact-view"
              data-testid="batch-impact-overview"
            >
              <BatchImpactMetrics summary={result.impact_summary} />
              <section className="batch-impact-review-section">
                <div className="batch-impact-section-heading">
                  <h4>Records Requiring QA Review</h4>
                  <p>Highest-priority connected records are grouped for comparison.</p>
                </div>
                <div className="batch-review-table-wrap">
                  <table className="batch-review-table">
                    <thead>
                      <tr>
                        <th scope="col">Priority</th>
                        <th scope="col">Area</th>
                        <th scope="col">Finding</th>
                        <th scope="col">Connected Records</th>
                        <th scope="col">Why It Matters</th>
                        <th scope="col">Recommended Review</th>
                        <th scope="col">Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleRows.map((row) => (
                        <tr key={row.id} className={`batch-review-row--${row.priority.toLowerCase()}`}>
                          <td><span className={`priority-badge priority-badge--${row.priority.toLowerCase()}`}>{row.priority}</span></td>
                          <td>{row.area}</td>
                          <td>{row.finding}</td>
                          <td>{row.connectedRecords.slice(0, 3).join(", ")}</td>
                          <td>{row.whyItMatters}</td>
                          <td>{row.recommendedReview}</td>
                          <td>
                            <button type="button" className="text-action" onClick={() => openReviewDetails(row)}>
                              View
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="batch-review-card-list">
                  {visibleRows.map((row) => (
                    <article key={row.id} className={`batch-review-card batch-review-row--${row.priority.toLowerCase()}`}>
                      <div>
                        <span className={`priority-badge priority-badge--${row.priority.toLowerCase()}`}>{row.priority}</span>
                        <strong>{row.finding}</strong>
                      </div>
                      <p>{row.area}</p>
                      <p>{row.whyItMatters}</p>
                      <button type="button" className="text-action" onClick={() => openReviewDetails(row)}>
                        View details
                      </button>
                    </article>
                  ))}
                </div>
                {reviewRows.length > 6 ? (
                  <button type="button" className="text-action" onClick={() => setShowAllRows((value) => !value)}>
                    {showAllRows ? "Show fewer records" : "Show all records"}
                  </button>
                ) : null}
              </section>

              <section className="recommended-review-order">
                <div className="batch-impact-section-heading">
                  <h4>Recommended QA Review Order</h4>
                  <p>Start with the highest-value review actions linked to available evidence.</p>
                </div>
                <ol>
                  {topActions.map((action) => (
                    <li key={action.title}>
                      <div>
                        <strong>{action.title}</strong>
                        <p>{action.rationale}</p>
                      </div>
                      {evidenceButtonLabel(action) ? (
                        <button type="button" className="text-action" onClick={() => setSelectedAssessment(action)}>
                          View evidence
                        </button>
                      ) : null}
                    </li>
                  ))}
                </ol>
                {result.recommended_assessments.length > 3 ? (
                  <button type="button" className="text-action" onClick={() => setShowAllActions((value) => !value)}>
                    {showAllActions ? "Hide additional assessments" : "View all recommended assessments"}
                  </button>
                ) : null}
              </section>

              <p className="batch-impact-global-disclaimer">{limitation}</p>
            </section>
          ) : null}

          {activeTab === "map" ? (
            <section
              id="batch-impact-map"
              role="tabpanel"
              aria-labelledby="batch-impact-tab-map"
              className="batch-impact-view"
              data-testid="batch-impact-map-view"
            >
              <BatchImpactGraph
                nodes={result.nodes}
                edges={result.edges}
                summary={result.impact_summary}
                onNodeSelected={setSelectedNode}
                onEdgeSelected={setSelectedEdge}
              />
              {selectedEdge ? (
                <div className="batch-impact-edge-detail" data-testid="batch-impact-edge-detail">
                  <strong>Why is this connected?</strong>
                  <dl>
                    <div>
                      <dt>Relationship</dt>
                      <dd>{selectedEdge.relationship_label}</dd>
                    </div>
                    <div>
                      <dt>Why connected</dt>
                      <dd>{selectedEdge.why_connected}</dd>
                    </div>
                    <div>
                      <dt>Confidence</dt>
                      <dd>{percentText(selectedEdge.confidence)}</dd>
                    </div>
                    <div>
                      <dt>Limitation</dt>
                      <dd>{selectedEdge.limitation}</dd>
                    </div>
                  </dl>
                </div>
              ) : null}
            </section>
          ) : null}

          {activeTab === "details" ? (
            <section
              id="batch-impact-details"
              role="tabpanel"
              aria-labelledby="batch-impact-tab-details"
              className="batch-impact-view batch-impact-details-view"
              data-testid="batch-impact-details-view"
            >
              <details>
                <summary>Full Quality Signals</summary>
                <div className="quality-signal-list quality-signal-list--compact">
                  {reviewRows.map((row) => {
                    const signal = result.signals.find((item) => `${item.category}-${item.name}` === row.id);
                    return signal ? <QualitySignalCard key={row.id} signal={signal} /> : null;
                  })}
                </div>
              </details>
              <details>
                <summary>Full Recommended Assessments</summary>
                <ul className="recommended-assessments recommended-assessments--compact">
                  {result.recommended_assessments.map((assessment) => (
                    <li key={assessment.title}>
                      <strong>{assessment.title}</strong>
                      <p>{assessment.rationale}</p>
                      <span>Evidence: {assessment.evidence_record_ids.length ? assessment.evidence_record_ids.join(", ") : "Not provided"}</span>
                    </li>
                  ))}
                </ul>
              </details>
              <details>
                <summary>Data Limitations</summary>
                <ul className="batch-impact-limitations-list">
                  {[...new Set([...result.limitations, ...result.impact_summary.data_limitations])].map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </details>
              <details>
                <summary>Evidence References</summary>
                <ul className="batch-impact-evidence-list">
                  {result.nodes.filter((node) => node.evidence_record_id).map((node) => (
                    <li key={node.id}>
                      <strong>{node.label}</strong>
                      <span>{node.evidence_record_id}</span>
                    </li>
                  ))}
                </ul>
              </details>
            </section>
          ) : null}
        </div>
      ) : null}

      <NodeDetailDrawer node={selectedNode} onClose={() => setSelectedNode(null)} />
      <NodeDetailDrawer
        node={selectedReviewRow ? {
          id: selectedReviewRow.id,
          type: "quality_signal",
          label: selectedReviewRow.finding,
          subtitle: selectedReviewRow.area,
          status: selectedReviewRow.priority,
          severity: selectedReviewRow.priority,
          evidence_record_id: selectedReviewRow.evidenceRecordIds.join(", ") || null,
          metadata: {
            connected_records: selectedReviewRow.connectedRecords,
            confidence: selectedReviewRow.confidence,
            why_connected: selectedReviewRow.whyItMatters,
            recommended_assessment: selectedReviewRow.recommendedReview,
            limitation: selectedReviewRow.limitation
          },
          position_hint: "quality"
        } : selectedAssessment ? {
          id: selectedAssessment.title,
          type: "recommended_assessment",
          label: selectedAssessment.title,
          subtitle: "Recommended QA review action",
          status: null,
          severity: null,
          evidence_record_id: selectedAssessment.evidence_record_ids.join(", ") || null,
          metadata: {
            rationale: selectedAssessment.rationale,
            evidence_record_ids: selectedAssessment.evidence_record_ids,
            limitation: selectedAssessment.limitation
          },
          position_hint: "quality"
        } : null}
        onClose={closeReviewDetails}
      />
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
