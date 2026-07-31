from __future__ import annotations

from app.agents.complaint.state import ComplaintAssistantState
from app.services.quality import evaluate_completeness, missing_field_labels


def missing_fields_from_complaint(existing_complaint: dict[str, object | None]) -> list[str]:
    return missing_field_labels(existing_complaint)


def check_completeness_node(state: ComplaintAssistantState) -> ComplaintAssistantState:
    completeness = evaluate_completeness(state["existing_complaint"])
    return {
        **state,
        "missing_fields": [*completeness.missing_critical_fields, *completeness.missing_recommended_fields],
        "completeness_result": completeness.model_dump(mode="json"),
    }
