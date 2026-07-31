from __future__ import annotations

from typing import NotRequired, TypedDict


class ComplaintAssistantMessageState(TypedDict):
    id: str
    role: str
    message_text: str
    created_at: str | None


class ComplaintAssistantState(TypedDict):
    request_id: str
    thread_id: str
    draft_id: str
    messages: list[ComplaintAssistantMessageState]
    latest_user_message: str
    attachment_id: str | None
    intent: str
    intent_confidence: float
    existing_complaint: dict[str, object | None]
    proposed_patch: dict[str, object] | None
    validated_patch: dict[str, object] | None
    changed_fields: list[str]
    conflict_fields: list[str]
    no_op_fields: list[str]
    field_evidence: list[dict[str, object]]
    missing_fields: list[str]
    initial_risk_assessment: dict[str, object] | None
    completeness_result: NotRequired[dict[str, object]]
    safety_routing_result: NotRequired[dict[str, object]]
    defect_classification_result: NotRequired[dict[str, object]]
    deterministic_safety_result: NotRequired[dict[str, object]]
    assistant_response: str
    clarification_required: bool
    clarification_question: str | None
    warnings: list[str]
    errors: list[str]
    provider: str | None
    requested_model: str | None
    actual_model: str | None
    prompt_versions: dict[str, str]
    run_started_at: str
    run_completed_at: str | None
    tool_name: NotRequired[str | None]
    tool_implemented: NotRequired[bool]
    extraction_result: NotRequired[dict[str, object]]
    accepted_field_metadata: NotRequired[dict[str, dict[str, object]]]
    pre_merge_complaint: NotRequired[dict[str, object | None]]
    persisted_user_message: NotRequired[dict[str, object]]
    persisted_assistant_message: NotRequired[dict[str, object]]
