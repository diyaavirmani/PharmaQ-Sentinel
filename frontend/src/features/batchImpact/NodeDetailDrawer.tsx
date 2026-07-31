import { OverlayDrawer } from "../../components/common/OverlayDrawer";
import type { BatchImpactNode } from "./batchImpactTypes";

interface NodeDetailDrawerProps {
  node: BatchImpactNode | null;
  onClose: () => void;
}

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function NodeDetailDrawer({ node, onClose }: NodeDetailDrawerProps) {
  return (
    <OverlayDrawer title={node ? `Batch Record: ${node.label}` : "Batch Record"} isOpen={Boolean(node)} onClose={onClose}>
      {node ? (
        <div className="batch-node-detail" data-testid="batch-node-detail-drawer">
          <span>{node.type.replace(/_/g, " ")}</span>
          <h3>{node.label}</h3>
          {node.subtitle ? <p>{node.subtitle}</p> : null}
          <dl>
            <div>
              <dt>Status</dt>
              <dd>{valueText(node.status)}</dd>
            </div>
            <div>
              <dt>Severity</dt>
              <dd>{valueText(node.severity)}</dd>
            </div>
            <div>
              <dt>Evidence Record ID</dt>
              <dd>{valueText(node.evidence_record_id)}</dd>
            </div>
          </dl>
          {Object.keys(node.metadata).length ? (
            <div>
              <h4>Metadata</h4>
              <dl>
                {Object.entries(node.metadata).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key.replace(/_/g, " ")}</dt>
                    <dd>{valueText(value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : null}
        </div>
      ) : null}
    </OverlayDrawer>
  );
}
