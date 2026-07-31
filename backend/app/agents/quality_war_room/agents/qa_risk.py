from __future__ import annotations

from typing import Any

from app.agents.quality_war_room.constants import SPECIALIST_NAMES
from app.agents.quality_war_room.schemas import SpecialistOutput


def _evidence_ids(context: dict[str, Any]) -> list[str]:
    return [item["evidence_id"] for item in context.get("evidence_index", [])[:5] if item.get("evidence_id")]


def run_qa_risk_agent(context: dict[str, Any]) -> SpecialistOutput:
    complaint = context.get("complaint", {})
    risk = context.get("risk_assessment") or {}
    evidence_ids = _evidence_ids(context)
    severity = complaint.get("suggested_severity") or risk.get("severity") or "UNDETERMINED"
    missing = complaint.get("missing_fields") or {}
    missing_count = len(missing) if isinstance(missing, list) else len(missing.keys()) if isinstance(missing, dict) else 0
    findings = [
        f"Draft severity signal is {severity}.",
        "Risk output remains a recommendation requiring QA review.",
    ]
    if missing_count:
        findings.append(f"{missing_count} complaint details are still missing or not provided.")
    return SpecialistOutput(
        agent_name=SPECIALIST_NAMES["qa"],
        concise_findings=findings,
        evidence_ids=evidence_ids,
        hypotheses=["Potential quality impact should be triaged against confirmed product, batch and defect details."],
        recommended_checks=["Verify complaint criticality against approved site SOP triage criteria."],
        immediate_considerations=["Preserve samples, attachments and source evidence before further review."],
        open_questions=["Are retain samples and customer samples available for comparison?"],
        confidence="MEDIUM" if evidence_ids else "LOW",
        limitations=["No authorized severity or regulatory decision is made by this run."],
    )
