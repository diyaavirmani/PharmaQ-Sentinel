from __future__ import annotations

from typing import Any

from app.agents.quality_war_room.constants import SPECIALIST_NAMES
from app.agents.quality_war_room.schemas import SpecialistOutput


def run_pharmacovigilance_agent(context: dict[str, Any]) -> SpecialistOutput:
    complaint = context.get("complaint", {})
    adverse_signal = bool(complaint.get("adverse_event_signal") or complaint.get("patient_consumed_product"))
    route = complaint.get("safety_route") or "UNDETERMINED"
    findings = [f"Safety route signal is {route}."]
    if adverse_signal:
        findings.append("Possible adverse-event information is present and needs PV triage.")
    else:
        findings.append("No explicit adverse-event signal is available in the scoped context.")
    return SpecialistOutput(
        agent_name=SPECIALIST_NAMES["pv"],
        concise_findings=findings,
        evidence_ids=[item["evidence_id"] for item in context.get("evidence_index", [])[:3] if item.get("evidence_id")],
        hypotheses=["Potential adverse-event reporting route should be assessed by qualified PV personnel."],
        recommended_checks=[
            "Confirm whether patient exposure, event timing and reporter contact details are available.",
            "Route possible adverse-event details for PV review when applicable.",
        ],
        immediate_considerations=["Do not delay quality complaint handling while PV triage is pending."],
        open_questions=["Is there an identifiable patient, reporter, product and adverse event?"],
        confidence="MEDIUM" if adverse_signal else "LOW",
        limitations=["This output is not medical advice or a final safety reportability decision."],
    )
