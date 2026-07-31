from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.complaint.constants import ComplaintAssistantIntent
from app.agents.complaint.nodes import (
    assess_initial_risk_node,
    check_completeness_node,
    classify_intent_node,
    create_response_node,
    execute_tool_node,
    handle_question_node,
    handle_unknown_node,
    load_context_node,
    merge_patch_node,
    persist_result_node,
    validate_patch_node,
)
from app.agents.complaint.state import ComplaintAssistantState
from app.models.base import utc_now
from app.repositories import AgentRunRepository
from app.services.llm import BaseLLMGateway, OpenAIModelGateway


@dataclass
class ComplaintAgentRuntime:
    db: Session
    agent_run: Any
    llm_gateway: BaseLLMGateway


def route_from_intent(state: ComplaintAssistantState) -> str:
    intent = ComplaintAssistantIntent(state["intent"])
    if intent in {
        ComplaintAssistantIntent.LOG_COMPLAINT,
        ComplaintAssistantIntent.EDIT_COMPLAINT,
        ComplaintAssistantIntent.EXTRACT_DOCUMENT,
    }:
        return "tool_patch_flow"
    if intent == ComplaintAssistantIntent.ASK_QUESTION:
        return "question"
    if intent in {
        ComplaintAssistantIntent.REQUEST_SUMMARY,
        ComplaintAssistantIntent.RUN_BATCH_IMPACT,
        ComplaintAssistantIntent.RUN_QUALITY_WAR_ROOM,
        ComplaintAssistantIntent.SAVE_COMPLAINT,
    }:
        return "tool_response_flow"
    return "unknown"


def build_complaint_graph(runtime: ComplaintAgentRuntime):
    graph = StateGraph(ComplaintAssistantState)
    graph.add_node("load_context", load_context_node(runtime))
    graph.add_node("classify_intent", classify_intent_node(runtime))
    graph.add_node("execute_tool", execute_tool_node(runtime))
    graph.add_node("validate_patch", validate_patch_node)
    graph.add_node("merge_patch", merge_patch_node(runtime))
    graph.add_node("check_completeness", check_completeness_node)
    graph.add_node("assess_initial_risk", assess_initial_risk_node(runtime))
    graph.add_node("persist_result", persist_result_node(runtime))
    graph.add_node("create_response", create_response_node)
    graph.add_node("handle_question", handle_question_node)
    graph.add_node("handle_unknown", handle_unknown_node)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_from_intent,
        {
            "tool_patch_flow": "execute_tool",
            "tool_response_flow": "execute_tool",
            "question": "handle_question",
            "unknown": "handle_unknown",
        },
    )
    graph.add_edge("execute_tool", "validate_patch")
    graph.add_edge("validate_patch", "merge_patch")
    graph.add_edge("merge_patch", "check_completeness")
    graph.add_edge("check_completeness", "assess_initial_risk")
    graph.add_edge("assess_initial_risk", "persist_result")
    graph.add_edge("handle_question", "persist_result")
    graph.add_edge("handle_unknown", "persist_result")
    graph.add_edge("persist_result", "create_response")
    graph.add_edge("create_response", END)
    return graph.compile()


def initial_state(
    *,
    request_id: str,
    draft_id: str,
    latest_user_message: str,
    attachment_id: str | None,
) -> ComplaintAssistantState:
    started_at = utc_now().isoformat()
    return {
        "request_id": request_id,
        "thread_id": "",
        "draft_id": draft_id,
        "messages": [],
        "latest_user_message": latest_user_message,
        "attachment_id": attachment_id,
        "intent": ComplaintAssistantIntent.UNKNOWN.value,
        "intent_confidence": 0,
        "existing_complaint": {},
        "proposed_patch": None,
        "validated_patch": None,
        "changed_fields": [],
        "conflict_fields": [],
        "no_op_fields": [],
        "field_evidence": [],
        "missing_fields": [],
        "initial_risk_assessment": None,
        "assistant_response": "",
        "clarification_required": False,
        "clarification_question": None,
        "warnings": [],
        "errors": [],
        "provider": None,
        "requested_model": None,
        "actual_model": None,
        "prompt_versions": {},
        "run_started_at": started_at,
        "run_completed_at": None,
        "tool_name": None,
        "tool_implemented": True,
    }


def run_complaint_assistant(
    *,
    db: Session,
    draft_id: str,
    request_id: str,
    latest_user_message: str,
    attachment_id: str | None = None,
    llm_gateway: BaseLLMGateway | None = None,
) -> ComplaintAssistantState:
    agent_run = AgentRunRepository(db).create_started(
        draft_id=draft_id,
        request_id=request_id,
        input_summary=f"user_message_length={len(latest_user_message)} attachment_present={attachment_id is not None}",
    )
    runtime = ComplaintAgentRuntime(
        db=db,
        agent_run=agent_run,
        llm_gateway=llm_gateway or OpenAIModelGateway(),
    )
    try:
        graph = build_complaint_graph(runtime)
        return graph.invoke(
            initial_state(
                request_id=request_id,
                draft_id=draft_id,
                latest_user_message=latest_user_message,
                attachment_id=attachment_id,
            )
        )
    except Exception as exc:
        AgentRunRepository(db).mark_completed(
            agent_run,
            intent=ComplaintAssistantIntent.UNKNOWN.value,
            tool_name=None,
            status="FAILED",
            errors_json={"errors": [exc.__class__.__name__]},
            output_summary="Graph execution failed before a safe assistant response was created.",
        )
        raise
