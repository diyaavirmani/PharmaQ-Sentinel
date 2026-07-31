from __future__ import annotations

from typing import Any

from app.agents.quality_war_room.constants import SPECIALIST_NAMES
from app.agents.quality_war_room.schemas import SpecialistOutput


def run_packaging_supplier_agent(context: dict[str, Any]) -> SpecialistOutput:
    complaint = context.get("complaint", {})
    batch_impact = context.get("batch_impact_summary") or {}
    signals = batch_impact.get("signals") or {}
    signal_count = len(signals.get("signals", [])) if isinstance(signals, dict) else 0
    defect = complaint.get("complaint_type") or "Not provided"
    findings = [f"Packaging/supplier review is scoped to complaint type {defect}."]
    if signal_count:
        findings.append(f"{signal_count} connected batch or supplier signals are available for QA review.")
    return SpecialistOutput(
        agent_name=SPECIALIST_NAMES["packaging"],
        concise_findings=findings,
        hypotheses=["Potential packaging material, packaging-line or supplier-lot association should be treated as a hypothesis."],
        recommended_checks=[
            "Inspect retained packaging components and line records.",
            "Check shared packaging material lots across related batches.",
        ],
        immediate_considerations=["Consider QA hold assessment for remaining inventory if packaging integrity is implicated."],
        open_questions=["Is the customer sample or damaged pack available for visual inspection?"],
        confidence="MEDIUM" if batch_impact else "LOW",
        limitations=["Supplier and packaging signals do not establish final responsibility."],
    )
