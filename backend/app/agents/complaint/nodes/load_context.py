from __future__ import annotations

from typing import Any

from app.agents.complaint.state import ComplaintAssistantState
from app.repositories import ComplaintDraftRepository, ComplaintMessageRepository, Pagination
from app.schemas.complaints import ComplaintDraftResponse


def load_context_node(runtime: Any):
    def node(state: ComplaintAssistantState) -> ComplaintAssistantState:
        draft = ComplaintDraftRepository(runtime.db).get_required(state["draft_id"])
        messages = ComplaintMessageRepository(runtime.db).list_for_draft(
            state["draft_id"],
            Pagination(limit=50, offset=0),
        )
        draft_snapshot = ComplaintDraftResponse.model_validate(draft).model_dump(mode="json")
        return {
            **state,
            "thread_id": draft.thread_id,
            "existing_complaint": draft_snapshot,
            "messages": [
                {
                    "id": message.id,
                    "role": message.role,
                    "message_text": message.message_text,
                    "created_at": message.created_at.isoformat() if message.created_at else None,
                }
                for message in messages
            ],
        }

    return node
