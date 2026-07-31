import type { BatchImpactSummary } from "./batchImpactTypes";

interface BatchImpactMetricsProps {
  summary: BatchImpactSummary;
}

const metricLabels = [
  ["Primary Batch", "primary_batch"],
  ["Related Batches", "related_batches"],
  ["Similar Complaints", "similar_complaint_count"],
  ["Open Deviations", "open_deviations"],
  ["Linked CAPAs", "linked_capas"],
  ["Distributed Quantity", "distributed_quantity"],
  ["Remaining Inventory", "remaining_inventory"],
  ["Priority", "overall_investigation_priority"]
] as const;

function metricValue(summary: BatchImpactSummary, key: (typeof metricLabels)[number][1]) {
  const value = summary[key];
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "None listed";
  }
  return String(value);
}

export function BatchImpactMetrics({ summary }: BatchImpactMetricsProps) {
  return (
    <div className="batch-impact-metrics" data-testid="batch-impact-metrics">
      {metricLabels.map(([label, key]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{metricValue(summary, key)}</strong>
        </div>
      ))}
    </div>
  );
}
