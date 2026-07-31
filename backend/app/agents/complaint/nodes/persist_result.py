from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.agents.complaint.state import ComplaintAssistantState
from app.models import MessageRole
from app.models.base import utc_now
from app.repositories import AgentRunRepository, ComplaintMessageRepository


def _message_payload(message: object) -> dict[str, object]:
    return {
        "id": message.id,
        "draft_id": message.draft_id,
        "role": message.role,
        "message_text": message.message_text,
        "attachment_id": message.attachment_id,
        "created_at": message.created_at,
        "metadata_json": message.metadata_json,
    }


def _status_from_state(state: ComplaintAssistantState) -> str:
    if state["errors"]:
        return "FAILED"
    if not state.get("tool_implemented", True):
        return "NOT_IMPLEMENTED"
    if state["clarification_required"]:
        return "CLARIFICATION_REQUIRED"
    return "COMPLETED"


def persist_result_node(runtime: Any):
    def node(state: ComplaintAssistantState) -> ComplaintAssistantState:
        now = utc_now()
        message_repository = ComplaintMessageRepository(runtime.db)
        user_message_payload = state.get("persisted_user_message")
        user_message = None
        if user_message_payload is None:
            user_message = message_repository.add(
                draft_id=state["draft_id"],
                role=MessageRole.USER,
                message_text=state["latest_user_message"],
                attachment_id=state["attachment_id"],
                metadata_json={
                    "request_id": state["request_id"],
                    "intent": state["intent"],
                    "source": "complaint_assistant",
                },
                created_at=now,
            )
            user_message_payload = _message_payload(user_message)
        assistant_message = message_repository.add(
            draft_id=state["draft_id"],
            role=MessageRole.ASSISTANT,
            message_text=state["assistant_response"],
            created_at=now + timedelta(microseconds=1),
            metadata_json={
                "request_id": state["request_id"],
                "intent": state["intent"],
                "tool_name": state.get("tool_name"),
                "clarification_required": state["clarification_required"],
            },
        )
        AgentRunRepository(runtime.db).mark_completed(
            runtime.agent_run,
            intent=state["intent"],
            tool_name=state.get("tool_name"),
            status=_status_from_state(state),
            provider=state["provider"],
            requested_model=state["requested_model"],
            actual_model=state["actual_model"],
            output_summary=f"assistant_response_length={len(state['assistant_response'])}",
            warnings_json={"warnings": state["warnings"]},
            errors_json={"errors": state["errors"]} if state["errors"] else None,
        )
        return {
            **state,
            "persisted_user_message": user_message_payload,
            "persisted_assistant_message": _message_payload(assistant_message),
            "run_completed_at": utc_now().isoformat(),
        }

    return node
