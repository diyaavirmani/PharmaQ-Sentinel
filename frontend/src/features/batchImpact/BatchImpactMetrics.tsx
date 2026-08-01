import type { BatchImpactSummary } from "./batchImpactTypes";

interface BatchImpactMetricsProps {
  summary: BatchImpactSummary;
}

export function formatQuantity(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(numeric)} units`;
}

const metricItems = [
  {
    label: "Related Batches",
    value: (summary: BatchImpactSummary) => String(summary.related_batches.length),
    title: (summary: BatchImpactSummary) => summary.related_batches.join(", ") || "No related batches listed"
  },
  {
    label: "Markets",
    value: (summary: BatchImpactSummary) => String(summary.markets_or_locations.length),
    title: (summary: BatchImpactSummary) => summary.markets_or_locations.join(", ") || "No markets listed"
  },
  {
    label: "Distributed",
    value: (summary: BatchImpactSummary) => formatQuantity(summary.distributed_quantity)
  },
  {
    label: "Remaining Inventory",
    value: (summary: BatchImpactSummary) => formatQuantity(summary.remaining_inventory)
  },
  {
    label: "Open Deviations",
    value: (summary: BatchImpactSummary) => String(summary.open_deviations)
  },
  {
    label: "Linked CAPAs",
    value: (summary: BatchImpactSummary) => String(summary.linked_capas)
  }
] as const;

export function BatchImpactMetrics({ summary }: BatchImpactMetricsProps) {
  return (
    <div className="batch-impact-metrics" data-testid="batch-impact-metrics" aria-label="Batch Intelligence KPI summary">
      {metricItems.map((item) => (
        <div key={item.label} title={"title" in item ? item.title(summary) : undefined}>
          <span>{item.label}</span>
          <strong>{item.value(summary)}</strong>
        </div>
      ))}
    </div>
  );
}
