from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict


class QualityWarRoomState(TypedDict, total=False):
    run_id: str
    draft_id: str
    input_snapshot: dict[str, Any]
    complaint: dict[str, Any]
    evidence_index: list[dict[str, Any]]
    risk_assessment: dict[str, Any] | None
    batch_impact_summary: dict[str, Any] | None
    specialist_contexts: dict[str, dict[str, Any]]
    qa_output: dict[str, Any]
    manufacturing_output: dict[str, Any]
    packaging_output: dict[str, Any]
    pv_output: dict[str, Any]
    auditor_output: dict[str, Any]
    revision_requests: dict[str, list[str]]
    revised_outputs: dict[str, dict[str, Any]]
    consensus: dict[str, Any]
    warnings: list[str]
    errors: list[str]
    iteration_count: int
    max_iterations: int
    model_metadata: dict[str, Any]
    events: list[dict[str, Any]]
    started_at: datetime
    completed_at: datetime | None
