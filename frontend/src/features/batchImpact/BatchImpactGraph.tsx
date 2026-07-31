import { useMemo } from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { BatchImpactEdge, BatchImpactNode } from "./batchImpactTypes";
import { GraphLegend } from "./GraphLegend";

interface BatchImpactGraphProps {
  nodes: BatchImpactNode[];
  edges: BatchImpactEdge[];
  onNodeSelected: (node: BatchImpactNode) => void;
  onEdgeSelected: (edge: BatchImpactEdge) => void;
}

const positionsByHint: Record<string, { x: number; y: number }> = {
  origin: { x: 0, y: 160 },
  product: { x: 250, y: 160 },
  primary: { x: 500, y: 160 },
  related_batch: { x: 760, y: 80 },
  material: { x: 500, y: -70 },
  packaging: { x: 760, y: -70 },
  supplier: { x: 1010, y: -20 },
  line: { x: 500, y: 390 },
  equipment: { x: 760, y: 390 },
  quality: { x: 1010, y: 250 },
  complaint_history: { x: 1010, y: 100 },
  distribution: { x: 760, y: 610 },
  inventory: { x: 1010, y: 610 }
};

function nodeClassName(node: BatchImpactNode) {
  if (node.type === "complaint") {
    return "batch-impact-node batch-impact-node--complaint";
  }
  if (node.type === "batch") {
    return "batch-impact-node batch-impact-node--batch";
  }
  if (node.type.includes("material") || node.type === "supplier") {
    return "batch-impact-node batch-impact-node--material";
  }
  if (node.type === "distribution_location" || node.type === "warehouse_inventory") {
    return "batch-impact-node batch-impact-node--distribution";
  }
  if (node.type === "deviation" || node.type === "capa") {
    return "batch-impact-node batch-impact-node--quality";
  }
  return "batch-impact-node";
}

export function BatchImpactGraph({
  nodes,
  edges,
  onNodeSelected,
  onEdgeSelected
}: BatchImpactGraphProps) {
  const flowNodes = useMemo<Node[]>(
    () =>
      nodes.map((node, index) => {
        const base = positionsByHint[node.position_hint ?? ""] ?? {
          x: 250 + (index % 4) * 240,
          y: 100 + Math.floor(index / 4) * 150
        };
        return {
          id: node.id,
          position: {
            x: base.x,
            y: base.y + (index % 3) * 28
          },
          data: {
            label: (
              <div>
                <strong>{node.label}</strong>
                {node.subtitle ? <span>{node.subtitle}</span> : null}
              </div>
            )
          },
          className: nodeClassName(node)
        };
      }),
    [nodes]
  );
  const flowEdges = useMemo<Edge[]>(
    () =>
      edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.relationship_label,
        markerEnd: { type: MarkerType.ArrowClosed },
        className: "batch-impact-edge",
        data: { batchImpactEdge: edge }
      })),
    [edges]
  );
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);
  const edgeById = useMemo(() => new Map(edges.map((edge) => [edge.id, edge])), [edges]);

  return (
    <div className="batch-impact-graph-card" data-testid="batch-impact-graph">
      <div className="batch-impact-graph-card__header">
        <strong>Connected Records Graph</strong>
        <GraphLegend />
      </div>
      <div className="batch-impact-graph">
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          fitView
          minZoom={0.35}
          maxZoom={1.2}
          nodesDraggable={false}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          zoomOnDoubleClick={false}
          onNodeClick={(_event, node) => {
            const selected = nodeById.get(node.id);
            if (selected) {
              onNodeSelected(selected);
            }
          }}
          onEdgeClick={(_event, edge) => {
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
    </div>
  );
}
