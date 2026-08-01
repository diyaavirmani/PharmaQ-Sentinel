import { useMemo, useState } from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node,
  type ReactFlowInstance
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { BatchImpactEdge, BatchImpactNode, BatchImpactSummary } from "./batchImpactTypes";
import { GraphLegend } from "./GraphLegend";

interface BatchImpactGraphProps {
  nodes: BatchImpactNode[];
  edges: BatchImpactEdge[];
  summary: BatchImpactSummary;
  onNodeSelected: (node: BatchImpactNode) => void;
  onEdgeSelected: (edge: BatchImpactEdge) => void;
}

type GraphMode = "summary" | "all";
type GraphFilter = "all" | "batches" | "materials" | "equipment" | "quality" | "distribution";

const positionsByHint: Record<string, { x: number; y: number }> = {
  origin: { x: 0, y: 190 },
  product: { x: 260, y: 190 },
  primary: { x: 540, y: 190 },
  related_batch: { x: 850, y: 70 },
  material: { x: 850, y: -110 },
  packaging: { x: 850, y: -10 },
  supplier: { x: 1120, y: -40 },
  line: { x: 850, y: 300 },
  equipment: { x: 1120, y: 300 },
  quality: { x: 1120, y: 130 },
  complaint_history: { x: 1120, y: 20 },
  distribution: { x: 850, y: 500 },
  inventory: { x: 1120, y: 500 }
};

const filterOptions: Array<{ id: GraphFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "batches", label: "Batches" },
  { id: "materials", label: "Materials" },
  { id: "equipment", label: "Equipment" },
  { id: "quality", label: "Quality Events" },
  { id: "distribution", label: "Distribution" }
];

function categoryForNode(node: BatchImpactNode): GraphFilter {
  if (node.type === "batch") {
    return "batches";
  }
  if (node.type.includes("material") || node.type === "supplier") {
    return "materials";
  }
  if (node.type === "equipment" || node.type.includes("line")) {
    return "equipment";
  }
  if (node.type === "deviation" || node.type === "capa") {
    return "quality";
  }
  if (node.type === "distribution_location" || node.type === "warehouse_inventory") {
    return "distribution";
  }
  return "all";
}

function nodeClassName(node: BatchImpactNode, isDimmed: boolean) {
  const classes = ["batch-impact-node"];
  if (isDimmed) {
    classes.push("batch-impact-node--dimmed");
  }
  if (node.type === "complaint") {
    classes.push("batch-impact-node--complaint");
  } else if (node.type === "batch") {
    classes.push("batch-impact-node--batch");
  } else if (node.type.includes("material") || node.type === "supplier") {
    classes.push("batch-impact-node--material");
  } else if (node.type === "distribution_location" || node.type === "warehouse_inventory") {
    classes.push("batch-impact-node--distribution");
  } else if (node.type === "deviation" || node.type === "capa" || node.type === "quality_signal") {
    classes.push("batch-impact-node--quality");
  }
  return classes.join(" ");
}

function groupedNode(
  id: string,
  label: string,
  countLabel: string,
  records: BatchImpactNode[],
  positionHint: string
): BatchImpactNode {
  return {
    id,
    type: "quality_signal",
    label,
    subtitle: countLabel,
    status: null,
    severity: null,
    evidence_record_id: records.map((record) => record.evidence_record_id).filter(Boolean).join(", ") || null,
    metadata: {
      grouped_records: records.map((record) => ({
        label: record.label,
        type: record.type,
        status: record.status,
        evidence_record_id: record.evidence_record_id
      }))
    },
    position_hint: positionHint
  };
}

function buildSummaryGraph(nodes: BatchImpactNode[], summary: BatchImpactSummary) {
  const complaint = nodes.find((node) => node.type === "complaint");
  const product = nodes.find((node) => node.type === "product");
  const primaryBatch = nodes.find((node) => node.type === "batch" && node.label === summary.primary_batch) ?? nodes.find((node) => node.type === "batch");
  const relatedBatches = nodes.filter((node) => node.type === "batch" && node.id !== primaryBatch?.id);
  const materialRecords = nodes.filter((node) => node.type.includes("material") || node.type === "supplier");
  const equipmentRecords = nodes.filter((node) => node.type === "equipment" || node.type.includes("line"));
  const qualityRecords = nodes.filter((node) => node.type === "deviation" || node.type === "capa");
  const complaintHistory = nodes.filter((node) => node.type === "historical_complaint");
  const distributionRecords = nodes.filter((node) => node.type === "distribution_location" || node.type === "warehouse_inventory");
  const summaryNodes = [complaint, product, primaryBatch].filter(Boolean) as BatchImpactNode[];
  const groupedNodes = [
    relatedBatches.length ? groupedNode("group:related-batches", "Related Batches", `${relatedBatches.length} records`, relatedBatches, "related_batch") : null,
    materialRecords.length ? groupedNode("group:materials", "Materials", `${materialRecords.length} records`, materialRecords, "material") : null,
    equipmentRecords.length ? groupedNode("group:equipment", "Equipment / Line", `${equipmentRecords.length} records`, equipmentRecords, "equipment") : null,
    qualityRecords.length ? groupedNode("group:quality", "Quality Events", `${summary.open_deviations} deviation ? ${summary.linked_capas} CAPA`, qualityRecords, "quality") : null,
    complaintHistory.length ? groupedNode("group:history", "Complaint History", `${complaintHistory.length} records`, complaintHistory, "complaint_history") : null,
    distributionRecords.length ? groupedNode("group:distribution", "Distribution / Inventory", `${distributionRecords.length} records`, distributionRecords, "distribution") : null
  ].filter(Boolean) as BatchImpactNode[];
  const graphNodes = [...summaryNodes, ...groupedNodes];
  const graphEdges: BatchImpactEdge[] = [];
  if (complaint && product) {
    graphEdges.push({
      id: "summary:complaint-product",
      source: complaint.id,
      target: product.id,
      type: "SUMMARY_PATH",
      relationship_label: "Complaint product",
      source_record_ids: [complaint.id, product.id],
      why_connected: "The complaint is associated with this product context in the Batch Impact result.",
      limitation: "Connected records indicate assessment scope; they do not establish final quality impact or root cause.",
      confidence: null
    });
  }
  if (product && primaryBatch) {
    graphEdges.push({
      id: "summary:product-primary-batch",
      source: product.id,
      target: primaryBatch.id,
      type: "SUMMARY_PATH",
      relationship_label: "Product has batch",
      source_record_ids: [product.id, primaryBatch.id],
      why_connected: "The primary complaint batch is registered under the product context in the response.",
      limitation: "Connected records indicate assessment scope; they do not establish final quality impact or root cause.",
      confidence: null
    });
  }
  if (primaryBatch) {
    groupedNodes.forEach((node) => {
      graphEdges.push({
        id: `summary:${primaryBatch.id}-${node.id}`,
        source: primaryBatch.id,
        target: node.id,
        type: "SUMMARY_GROUP",
        relationship_label: node.label,
        source_record_ids: [primaryBatch.id, node.id],
        why_connected: `${node.label} are grouped from the Batch Impact response for review focus.`,
        limitation: "Connected records indicate assessment scope; they do not establish final quality impact or root cause.",
        confidence: null
      });
    });
  }
  return { nodes: graphNodes, edges: graphEdges };
}

function allRecordsPosition(node: BatchImpactNode, index: number) {
  const base = positionsByHint[node.position_hint ?? ""] ?? {
    x: 250 + (index % 4) * 240,
    y: 100 + Math.floor(index / 4) * 150
  };
  return {
    x: base.x,
    y: base.y + (index % 3) * 36
  };
}

function summaryPosition(node: BatchImpactNode) {
  const positions: Record<string, { x: number; y: number }> = {
    origin: { x: 0, y: 180 },
    product: { x: 250, y: 180 },
    primary: { x: 520, y: 180 },
    related_batch: { x: 820, y: 20 },
    material: { x: 820, y: 130 },
    equipment: { x: 820, y: 240 },
    quality: { x: 820, y: 350 },
    complaint_history: { x: 1120, y: 130 },
    distribution: { x: 1120, y: 270 }
  };
  return positions[node.position_hint ?? ""] ?? { x: 820, y: 180 };
}

export function BatchImpactGraph({
  nodes,
  edges,
  summary,
  onNodeSelected,
  onEdgeSelected
}: BatchImpactGraphProps) {
  const [mode, setMode] = useState<GraphMode>("summary");
  const [filter, setFilter] = useState<GraphFilter>("all");
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [instance, setInstance] = useState<ReactFlowInstance | null>(null);
  const summaryGraph = useMemo(() => buildSummaryGraph(nodes, summary), [nodes, summary]);
  const visibleSource = mode === "summary" ? summaryGraph : { nodes, edges };
  const visibleNodes = useMemo(
    () =>
      visibleSource.nodes.filter((node) => {
        if (filter === "all" || mode === "summary") {
          return true;
        }
        const category = categoryForNode(node);
        return category === filter || category === "all";
      }),
    [filter, mode, visibleSource.nodes]
  );
  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);
  const visibleEdges = useMemo(
    () => visibleSource.edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)),
    [visibleEdgesKey(visibleSource.edges), visibleNodeIds]
  );
  const connectedToSelection = useMemo(() => {
    if (!selectedNodeId) {
      return new Set<string>();
    }
    const connected = new Set([selectedNodeId]);
    visibleEdges.forEach((edge) => {
      if (edge.source === selectedNodeId) {
        connected.add(edge.target);
      }
      if (edge.target === selectedNodeId) {
        connected.add(edge.source);
      }
    });
    return connected;
  }, [selectedNodeId, visibleEdges]);
  const flowNodes = useMemo<Node[]>(
    () =>
      visibleNodes.map((node, index) => {
        const position = mode === "summary" ? summaryPosition(node) : allRecordsPosition(node, index);
        const isDimmed = selectedNodeId !== null && !connectedToSelection.has(node.id);
        return {
          id: node.id,
          position,
          data: {
            label: (
              <div>
                <strong>{node.label}</strong>
                {node.subtitle ? <span>{node.subtitle}</span> : null}
              </div>
            )
          },
          className: nodeClassName(node, isDimmed)
        };
      }),
    [connectedToSelection, mode, selectedNodeId, visibleNodes]
  );
  const flowEdges = useMemo<Edge[]>(
    () =>
      visibleEdges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        markerEnd: { type: MarkerType.ArrowClosed },
        className: edge.id === selectedEdgeId ? "batch-impact-edge batch-impact-edge--selected" : "batch-impact-edge",
        data: { batchImpactEdge: edge }
      })),
    [selectedEdgeId, visibleEdges]
  );
  const nodeById = useMemo(() => new Map(visibleNodes.map((node) => [node.id, node])), [visibleNodes]);
  const edgeById = useMemo(() => new Map(visibleEdges.map((edge) => [edge.id, edge])), [visibleEdges]);

  return (
    <div className="batch-impact-graph-card" data-testid="batch-impact-graph">
      <div className="batch-impact-graph-card__header">
        <strong>Relationship Map</strong>
        <GraphLegend />
      </div>
      <div className="batch-impact-map-controls" aria-label="Relationship map controls">
        <div className="segmented-control" role="group" aria-label="Relationship map mode">
          <button type="button" aria-pressed={mode === "summary"} onClick={() => setMode("summary")}>
            Summary View
          </button>
          <button type="button" aria-pressed={mode === "all"} onClick={() => setMode("all")}>
            All Records
          </button>
        </div>
        <div className="batch-impact-filter-chips" role="group" aria-label="Relationship map filters">
          {filterOptions.map((option) => (
            <button
              key={option.id}
              type="button"
              aria-pressed={filter === option.id}
              onClick={() => setFilter(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>
        <button type="button" className="text-action" onClick={() => instance?.fitView({ padding: 0.18, duration: 250 })}>
          Fit View
        </button>
      </div>
      <div className="batch-impact-graph">
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          fitView
          minZoom={0.45}
          maxZoom={1.35}
          nodesDraggable={false}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch
          zoomOnDoubleClick={false}
          onInit={setInstance}
          onNodeClick={(_event, node) => {
            setSelectedNodeId(node.id);
            const selected = nodeById.get(node.id);
            if (selected) {
              onNodeSelected(selected);
            }
          }}
          onEdgeClick={(_event, edge) => {
            setSelectedEdgeId(edge.id);
            const selected = edgeById.get(edge.id);
            if (selected) {
              onEdgeSelected(selected);
            }
          }}
        >
          <Background gap={18} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="batch-impact-edge-picks" aria-label="Relationship explanations">
        {visibleEdges.slice(0, 8).map((edge) => (
          <button
            key={edge.id}
            type="button"
            className="text-action"
            onClick={() => {
              setSelectedEdgeId(edge.id);
              onEdgeSelected(edge);
            }}
          >
            {edge.relationship_label}
          </button>
        ))}
      </div>
    </div>
  );
}

function visibleEdgesKey(edges: BatchImpactEdge[]) {
  return edges.map((edge) => edge.id).join("|");
}
