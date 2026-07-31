import type { QualityWarRoomRunResponse } from "./qualityWarRoomTypes";

interface PreviousRunsSelectorProps {
  runs: QualityWarRoomRunResponse[];
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
}

export function PreviousRunsSelector({ runs, selectedRunId, onSelectRun }: PreviousRunsSelectorProps) {
  if (!runs.length) {
    return null;
  }
  return (
    <label className="previous-runs-selector">
      Previous runs
      <select value={selectedRunId ?? ""} onChange={(event) => onSelectRun(event.target.value)}>
        {runs.map((run) => (
          <option key={run.id} value={run.id}>
            {new Date(run.started_at).toLocaleString()} · {run.status}
          </option>
        ))}
      </select>
    </label>
  );
}
