from __future__ import annotations

from typing import Any

from app.agents.quality_war_room.constants import SPECIALIST_NAMES
from app.agents.quality_war_room.schemas import SpecialistOutput


def run_manufacturing_agent(context: dict[str, Any]) -> SpecialistOutput:
    complaint = context.get("complaint", {})
    batch_impact = context.get("batch_impact_summary") or {}
    summary = batch_impact.get("summary") or {}
    batch_number = complaint.get("batch_lot_number") or "Not provided"
    related_batches = summary.get("related_batches") or []
    open_deviations = summary.get("open_deviations")
    findings = [f"Manufacturing review scope is anchored to batch {batch_number}."]
    if related_batches:
        findings.append(f"Related batches available for comparison: {', '.join(related_batches)}.")
    if open_deviations is not None:
        findings.append(f"Open deviation count in reference context: {open_deviations}.")
    return SpecialistOutput(
        agent_name=SPECIALIST_NAMES["manufacturing"],
        concise_findings=findings,
        evidence_ids=[],
        hypotheses=["Potential process or line association should be checked against batch records and deviations."],
        recommended_checks=[
            "Review batch manufacturing record and line clearance records.",
            "Compare retain sample observations with the complaint description.",
        ],
        immediate_considerations=["Assess whether any in-process controls or release tests require QA review."],
        open_questions=["Were any atypical events recorded during manufacturing or packaging?"],
        confidence="MEDIUM" if batch_impact else "LOW",
        limitations=["Reference manufacturing records are fictional demonstration data."],
    )
