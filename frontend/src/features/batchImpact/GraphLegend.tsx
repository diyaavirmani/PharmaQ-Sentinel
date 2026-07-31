const legendItems = [
  ["Complaint", "batch-impact-node--complaint"],
  ["Batch", "batch-impact-node--batch"],
  ["Material", "batch-impact-node--material"],
  ["Quality", "batch-impact-node--quality"],
  ["Distribution", "batch-impact-node--distribution"]
];

export function GraphLegend() {
  return (
    <div className="batch-impact-legend" aria-label="Batch graph legend">
      {legendItems.map(([label, className]) => (
        <span key={label}>
          <i className={className} aria-hidden="true" />
          {label}
        </span>
      ))}
    </div>
  );
}
