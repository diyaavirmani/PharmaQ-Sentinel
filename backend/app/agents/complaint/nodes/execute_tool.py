from __future__ import annotations

from app.agents.complaint.constants import UNIMPLEMENTED_TOOL_MESSAGE, ComplaintAssistantIntent
from app.agents.complaint.state import ComplaintAssistantState
from app.agents.complaint.tools import (
    build_edit_complaint_state,
    build_extract_document_state,
    build_log_complaint_state,
    summarize_complaint,
)


def execute_tool_node(runtime: object):
    def node(state: ComplaintAssistantState) -> ComplaintAssistantState:
        intent = ComplaintAssistantIntent(state["intent"])

        if intent == ComplaintAssistantIntent.LOG_COMPLAINT:
            return build_log_complaint_state(runtime, state)
        if intent == ComplaintAssistantIntent.EDIT_COMPLAINT:
            return build_edit_complaint_state(runtime, state)
        elif intent == ComplaintAssistantIntent.EXTRACT_DOCUMENT:
            return build_extract_document_state(runtime, state)
        elif intent == ComplaintAssistantIntent.REQUEST_SUMMARY:
            return {
                **state,
                "tool_name": "summarize_complaint",
                "tool_implemented": True,
                "assistant_response": summarize_complaint(state["existing_complaint"]),
                "changed_fields": [],
            }
        elif intent == ComplaintAssistantIntent.RUN_BATCH_IMPACT:
            return {
                **state,
                "tool_name": "batch_impact",
                "tool_implemented": False,
                "assistant_response": "Batch impact analysis is not implemented in this phase. No complaint fields were changed.",
                "changed_fields": [],
                "warnings": [*state["warnings"], UNIMPLEMENTED_TOOL_MESSAGE],
            }
        elif intent == ComplaintAssistantIntent.RUN_QUALITY_WAR_ROOM:
            return {
                **state,
                "tool_name": "quality_war_room",
                "tool_implemented": False,
                "assistant_response": "Quality War Room is not implemented in this phase. No complaint fields were changed.",
                "changed_fields": [],
                "warnings": [*state["warnings"], UNIMPLEMENTED_TOOL_MESSAGE],
            }
        elif intent == ComplaintAssistantIntent.SAVE_COMPLAINT:
            return {
                **state,
                "tool_name": "save_complaint_guidance",
                "tool_implemented": False,
                "assistant_response": "Please review the read-only complaint form and use the existing Save Complaint action when the reviewed draft is ready. No complaint fields were changed.",
                "changed_fields": [],
            }
        else:
            return state

    return node
