from __future__ import annotations

from app.agents.complaint.nodes.check_completeness import missing_fields_from_complaint
from app.agents.complaint.state import ComplaintAssistantState
from app.agents.complaint.tools.summarize_complaint import summarize_complaint


def _format_value(value: object | None) -> str:
    return "Not provided" if value in (None, "") else str(value)


def _risk_metadata(complaint: dict[str, object | None]) -> dict[str, object]:
    missing_fields = complaint.get("missing_fields")
    if isinstance(missing_fields, dict) and isinstance(missing_fields.get("risk"), dict):
        return missing_fields["risk"]
    return {}


def handle_question_node(state: ComplaintAssistantState) -> ComplaintAssistantState:
    lowered = state["latest_user_message"].lower()
    complaint = state["existing_complaint"]

    if "missing" in lowered:
        missing_fields = missing_fields_from_complaint(complaint)
        if not missing_fields:
            response = "No required review fields are currently marked as missing."
        else:
            response = "Currently missing: " + ", ".join(missing_fields) + "."
        return {
            **state,
            "missing_fields": missing_fields,
            "assistant_response": response,
            "changed_fields": [],
        }

    if "batch" in lowered:
        return {
            **state,
            "assistant_response": f"Current batch or lot number: {_format_value(complaint.get('batch_lot_number'))}.",
            "changed_fields": [],
        }

    if "risk" in lowered or "severity" in lowered or "route" in lowered:
        risk = _risk_metadata(complaint)
        routes = risk.get("route_chips") if isinstance(risk.get("route_chips"), list) else []
        route_text = ", ".join(str(route).replace("_", " ").title() for route in routes) or _format_value(complaint.get("safety_route"))
        return {
            **state,
            "assistant_response": (
                f"Current draft severity suggestion: {_format_value(complaint.get('suggested_severity'))}. "
                f"Priority suggestion: {_format_value(complaint.get('suggested_priority'))}. "
                f"Suggested review route: {route_text}. These are draft suggestions requiring authorised QA review."
            ),
            "changed_fields": [],
        }

    if "summar" in lowered:
        return {
            **state,
            "assistant_response": summarize_complaint(complaint),
            "changed_fields": [],
        }

    return {
        **state,
        "assistant_response": "I can answer questions about the currently stored draft, such as missing information, batch number, risk, safety route, severity, or a summary.",
        "clarification_required": True,
        "clarification_question": "Which current draft detail would you like to review?",
        "changed_fields": [],
    }
