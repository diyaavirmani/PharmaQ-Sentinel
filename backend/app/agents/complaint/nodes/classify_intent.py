from __future__ import annotations

from typing import Any

from app.agents.complaint.constants import (
    PROMPT_VERSION_INTENT_ROUTER,
    ComplaintAssistantIntent,
)
from app.agents.complaint.prompts import INTENT_ROUTER_PROMPT
from app.agents.complaint.schemas import ComplaintIntentClassification
from app.agents.complaint.state import ComplaintAssistantState
from app.services.llm import LLMGatewayError, LLMRequestContext


def _deterministic_classification(
    *,
    message: str,
    attachment_id: str | None,
) -> ComplaintIntentClassification | None:
    lowered = message.lower()
    if attachment_id:
        return ComplaintIntentClassification(
            intent=ComplaintAssistantIntent.EXTRACT_DOCUMENT,
            confidence=0.95,
            reason_summary="Attachment was provided.",
        )
    if any(phrase in lowered for phrase in ("save complaint", "commit complaint", "submit complaint")):
        return ComplaintIntentClassification(
            intent=ComplaintAssistantIntent.SAVE_COMPLAINT,
            confidence=0.92,
            reason_summary="User requested saving or committing the complaint.",
        )
    if "batch impact" in lowered or "blast radius" in lowered:
        return ComplaintIntentClassification(
            intent=ComplaintAssistantIntent.RUN_BATCH_IMPACT,
            confidence=0.92,
            reason_summary="User requested batch impact analysis.",
        )
    if "war room" in lowered or "quality war" in lowered:
        return ComplaintIntentClassification(
            intent=ComplaintAssistantIntent.RUN_QUALITY_WAR_ROOM,
            confidence=0.92,
            reason_summary="User requested Quality War Room.",
        )
    if any(
        term in lowered
        for term in (
            "actually",
            "change ",
            "clear ",
            "contact is",
            "correct ",
            "complaint date is",
            "instead",
            "not ",
            "remove ",
            "sorry",
            "should be",
            "update ",
            "was not provided",
            "replace ",
        )
    ):
        return ComplaintIntentClassification(
            intent=ComplaintAssistantIntent.EDIT_COMPLAINT,
            confidence=0.82,
            reason_summary="User appears to be correcting existing draft information.",
        )
    if any(term in lowered for term in ("summarise", "summarize", "summary")):
        return ComplaintIntentClassification(
            intent=ComplaintAssistantIntent.REQUEST_SUMMARY,
            confidence=0.88,
            reason_summary="User requested a summary.",
        )
    if any(term in lowered for term in ("what is missing", "missing information", "current batch", "batch number", "severity", "what fields")):
        return ComplaintIntentClassification(
            intent=ComplaintAssistantIntent.ASK_QUESTION,
            confidence=0.9,
            reason_summary="User asked about current draft information.",
        )
    if "?" in lowered or lowered.startswith(("what ", "which ", "is ", "are ", "can ", "does ")):
        return ComplaintIntentClassification(
            intent=ComplaintAssistantIntent.ASK_QUESTION,
            confidence=0.76,
            reason_summary="User asked a question.",
        )
    if any(term in lowered for term in ("complaint", "reported", "customer", "batch", "defect")) and len(lowered) > 40:
        return ComplaintIntentClassification(
            intent=ComplaintAssistantIntent.LOG_COMPLAINT,
            confidence=0.78,
            reason_summary="User appears to be providing complaint narrative text.",
        )
    return None


def classify_intent_node(runtime: Any):
    def node(state: ComplaintAssistantState) -> ComplaintAssistantState:
        deterministic = _deterministic_classification(
            message=state["latest_user_message"],
            attachment_id=state["attachment_id"],
        )
        if deterministic is not None:
            return {
                **state,
                "intent": deterministic.intent.value,
                "intent_confidence": deterministic.confidence,
                "clarification_required": deterministic.clarification_required,
                "clarification_question": deterministic.clarification_question,
                "prompt_versions": {
                    **state["prompt_versions"],
                    "intent_router": "deterministic-v1",
                },
            }

        try:
            result = runtime.llm_gateway.generate_structured(
                system_instructions=INTENT_ROUTER_PROMPT,
                user_input=state["latest_user_message"],
                response_schema=ComplaintIntentClassification,
                request_context=LLMRequestContext(
                    request_id=state["request_id"],
                    draft_id=state["draft_id"],
                    thread_id=state["thread_id"],
                    tool_name="complaint_intent_router",
                    purpose="Classify complaint assistant intent",
                    actor_identifier=None,
                    prompt_version=PROMPT_VERSION_INTENT_ROUTER,
                    contains_sensitive_information=True,
                    metadata={"message_length": len(state["latest_user_message"])},
                ),
                temperature=0,
                max_output_tokens=250,
            )
            classification = result.parsed_output
            return {
                **state,
                "intent": classification.intent.value,
                "intent_confidence": classification.confidence,
                "clarification_required": classification.clarification_required,
                "clarification_question": classification.clarification_question,
                "provider": result.provider,
                "requested_model": result.requested_model,
                "actual_model": result.actual_model,
                "prompt_versions": {
                    **state["prompt_versions"],
                    "intent_router": result.prompt_version,
                },
                "warnings": [*state["warnings"], *result.warnings],
            }
        except LLMGatewayError:
            return {
                **state,
                "intent": ComplaintAssistantIntent.UNKNOWN.value,
                "intent_confidence": 0,
                "clarification_required": True,
                "clarification_question": "Please tell me whether you want to log a complaint, ask a question, or review the current draft.",
                "warnings": [
                    *state["warnings"],
                    "AI intent classification was unavailable; used safe fallback.",
                ],
            }

    return node
