from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.quality_war_room.agents.compliance_auditor import run_compliance_auditor
from app.agents.quality_war_room.agents.manufacturing import run_manufacturing_agent
from app.agents.quality_war_room.agents.packaging_supplier import run_packaging_supplier_agent
from app.agents.quality_war_room.agents.pharmacovigilance import run_pharmacovigilance_agent
from app.agents.quality_war_room.agents.qa_risk import run_qa_risk_agent
from app.agents.quality_war_room.consensus import build_consensus
from app.agents.quality_war_room.constants import (
    MAX_SPECIALIST_PASSES,
    MODEL_NAME,
    PROVIDER_NAME,
    SPECIALIST_NAMES,
    SPECIALIST_TIMEOUT_SECONDS,
)
from app.agents.quality_war_room.context_builder import build_quality_war_room_context
from app.agents.quality_war_room.schemas import SpecialistOutput
from app.agents.quality_war_room.state import QualityWarRoomState
from app.models.base import new_uuid, utc_now
from app.repositories.quality_war_room import (
    QualityWarRoomEventRepository,
    QualityWarRoomRunRepository,
)

SpecialistFn = Callable[[dict[str, Any]], SpecialistOutput]

SPECIALIST_FUNCTIONS: dict[str, SpecialistFn] = {
    "qa": run_qa_risk_agent,
    "manufacturing": run_manufacturing_agent,
    "packaging": run_packaging_supplier_agent,
    "pv": run_pharmacovigilance_agent,
}


def _event(
    event_type: str,
    message: str,
    *,
    agent_name: str | None = None,
    status: str = "COMPLETE",
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "agent_name": agent_name,
        "status": status,
        "concise_message": message,
        "evidence_ids": evidence_ids or [],
        "created_at": utc_now(),
    }


def _failed_output(key: str, message: str) -> SpecialistOutput:
    return SpecialistOutput(
        agent_name=SPECIALIST_NAMES[key],
        status="FAILED",
        concise_findings=[],
        open_questions=[message],
        confidence="LOW",
        limitations=["Specialist output was unavailable; consensus preserves this limitation."],
    )


def prepare_context_node(db: Session):
    def _node(state: QualityWarRoomState) -> QualityWarRoomState:
        context = build_quality_war_room_context(db, state["draft_id"])
        return {
            **state,
            **context,
            "events": [
                *state.get("events", []),
                _event("war_room_started", "Quality War Room run started.", status="STARTED"),
                _event("context_prepared", "Complaint, evidence and permitted context prepared."),
            ],
        }

    return _node


def run_specialists_node(state: QualityWarRoomState) -> QualityWarRoomState:
    contexts = state["specialist_contexts"]
    events = list(state.get("events", []))
    outputs: dict[str, SpecialistOutput] = {}

    for key in SPECIALIST_FUNCTIONS:
        events.append(_event(f"{key}_agent_started", f"{SPECIALIST_NAMES[key]} started.", agent_name=SPECIALIST_NAMES[key], status="STARTED"))

    with ThreadPoolExecutor(max_workers=len(SPECIALIST_FUNCTIONS)) as executor:
        futures = {
            executor.submit(function, contexts[key]): key
            for key, function in SPECIALIST_FUNCTIONS.items()
        }
        try:
            for future in as_completed(futures, timeout=SPECIALIST_TIMEOUT_SECONDS):
                key = futures[future]
                try:
                    output = future.result(timeout=0)
                except Exception as exc:  # noqa: BLE001  # Specialist failures must not abort the run.
                    output = _failed_output(key, f"{SPECIALIST_NAMES[key]} failed: {exc.__class__.__name__}")
                outputs[key] = output
                events.append(
                    _event(
                        f"{key}_agent_completed",
                        f"{output.agent_name} completed with {output.confidence.lower()} confidence.",
                        agent_name=output.agent_name,
                        status=output.status,
                        evidence_ids=output.evidence_ids,
                    )
                )
        except TimeoutError:
            pass

    for key in SPECIALIST_FUNCTIONS:
        if key not in outputs:
            output = _failed_output(key, f"{SPECIALIST_NAMES[key]} timed out.")
            outputs[key] = output
            events.append(
                _event(
                    f"{key}_agent_completed",
                    f"{output.agent_name} unavailable after timeout.",
                    agent_name=output.agent_name,
                    status=output.status,
                )
            )

    return {
        **state,
        "qa_output": outputs["qa"].model_dump(mode="json"),
        "manufacturing_output": outputs["manufacturing"].model_dump(mode="json"),
        "packaging_output": outputs["packaging"].model_dump(mode="json"),
        "pv_output": outputs["pv"].model_dump(mode="json"),
        "events": events,
    }


def auditor_node(state: QualityWarRoomState) -> QualityWarRoomState:
    outputs = {
        "qa": SpecialistOutput.model_validate(state["qa_output"]),
        "manufacturing": SpecialistOutput.model_validate(state["manufacturing_output"]),
        "packaging": SpecialistOutput.model_validate(state["packaging_output"]),
        "pv": SpecialistOutput.model_validate(state["pv_output"]),
    }
    events = [
        *state.get("events", []),
        _event("auditor_started", "Compliance Auditor started.", agent_name="Compliance Auditor", status="STARTED"),
    ]
    auditor = run_compliance_auditor(outputs)
    for agent_key, requests in auditor.specialist_revision_requests.items():
        for request in requests:
            events.append(
                _event(
                    "auditor_challenge",
                    request,
                    agent_name=SPECIALIST_NAMES.get(agent_key, agent_key),
                    status="CHALLENGE",
                )
            )
    events.append(_event("auditor_completed", "Compliance Auditor completed.", agent_name="Compliance Auditor"))
    return {
        **state,
        "auditor_output": auditor.model_dump(mode="json"),
        "revision_requests": auditor.specialist_revision_requests,
        "events": events,
    }


def should_revise(state: QualityWarRoomState) -> str:
    if state.get("revision_requests") and state.get("iteration_count", 1) < MAX_SPECIALIST_PASSES:
        return "revise"
    return "consensus"


def revision_node(state: QualityWarRoomState) -> QualityWarRoomState:
    events = [
        *state.get("events", []),
        _event("revision_started", "Bounded specialist revision pass started.", status="STARTED"),
    ]
    revised_outputs: dict[str, dict[str, Any]] = {}
    for key in state.get("revision_requests", {}):
        current = SpecialistOutput.model_validate(state[f"{key}_output"])
        revised = current.model_copy(
            update={
                "hypotheses": [
                    claim.replace("confirmed root cause", "potential contributing factor")
                    for claim in current.hypotheses
                ],
                "limitations": [*current.limitations, "Revised after compliance challenge."],
            }
        )
        revised_outputs[key] = revised.model_dump(mode="json")
    updated_state: QualityWarRoomState = {
        **state,
        "iteration_count": state.get("iteration_count", 1) + 1,
        "revised_outputs": revised_outputs,
        "events": [
            *events,
            _event("revision_completed", "Bounded specialist revision pass completed."),
        ],
    }
    for key, output in revised_outputs.items():
        updated_state[f"{key}_output"] = output
    return updated_state


def consensus_node(state: QualityWarRoomState) -> QualityWarRoomState:
    outputs = {
        "qa": SpecialistOutput.model_validate(state["qa_output"]),
        "manufacturing": SpecialistOutput.model_validate(state["manufacturing_output"]),
        "packaging": SpecialistOutput.model_validate(state["packaging_output"]),
        "pv": SpecialistOutput.model_validate(state["pv_output"]),
    }
    auditor = run_compliance_auditor(outputs, revision_counts={key: 1 for key in state.get("revision_requests", {})})
    consensus = build_consensus(
        complaint=state["complaint"],
        specialist_outputs=outputs,
        auditor_output=auditor,
    )
    return {
        **state,
        "auditor_output": auditor.model_dump(mode="json"),
        "consensus": consensus.model_dump(mode="json"),
        "completed_at": utc_now(),
        "events": [
            *state.get("events", []),
            _event("consensus_started", "Consensus Agent started.", agent_name="Consensus Agent", status="STARTED"),
            _event("consensus_completed", "Consensus Agent completed.", agent_name="Consensus Agent", evidence_ids=consensus.evidence_ids),
        ],
    }


def persist_run_node(db: Session):
    def _node(state: QualityWarRoomState) -> QualityWarRoomState:
        started_at = state["started_at"]
        completed_at = state.get("completed_at") or utc_now()
        run = QualityWarRoomRunRepository(db).append(
            run_id=state["run_id"],
            draft_id=state["draft_id"],
            input_snapshot=state["input_snapshot"],
            status="COMPLETE" if not state.get("errors") else "PARTIAL",
            iteration_count=state.get("iteration_count", 1),
            specialist_outputs_json={
                "qa": state["qa_output"],
                "manufacturing": state["manufacturing_output"],
                "packaging": state["packaging_output"],
                "pv": state["pv_output"],
            },
            auditor_output_json=state["auditor_output"],
            consensus_json=state["consensus"],
            provider=PROVIDER_NAME,
            model=MODEL_NAME,
            started_at=started_at,
            completed_at=completed_at,
            error_summary="; ".join(state.get("errors", [])) or None,
        )
        event_repository = QualityWarRoomEventRepository(db)
        for index, event in enumerate(state.get("events", [])):
            event_repository.append(
                run_id=run.id,
                event_type=event["event_type"],
                agent_name=event.get("agent_name"),
                status=event["status"],
                concise_message=event["concise_message"],
                evidence_ids=event.get("evidence_ids"),
                created_at=started_at + timedelta(microseconds=index + 1),
            )
        event_repository.append(
            run_id=run.id,
            event_type="war_room_completed",
            agent_name=None,
            status=run.status,
            concise_message="Quality War Room run persisted.",
            evidence_ids=state["consensus"].get("evidence_ids", []),
            created_at=completed_at,
        )
        return state

    return _node


def build_quality_war_room_graph(db: Session):
    graph = StateGraph(QualityWarRoomState)
    graph.add_node("prepare_context", prepare_context_node(db))
    graph.add_node("run_specialists", run_specialists_node)
    graph.add_node("compliance_auditor", auditor_node)
    graph.add_node("revision", revision_node)
    graph.add_node("consensus", consensus_node)
    graph.add_node("persist_run", persist_run_node(db))
    graph.add_edge(START, "prepare_context")
    graph.add_edge("prepare_context", "run_specialists")
    graph.add_edge("run_specialists", "compliance_auditor")
    graph.add_conditional_edges("compliance_auditor", should_revise, {"revise": "revision", "consensus": "consensus"})
    graph.add_edge("revision", "consensus")
    graph.add_edge("consensus", "persist_run")
    graph.add_edge("persist_run", END)
    return graph.compile()


def run_quality_war_room(db: Session, *, draft_id: str) -> str:
    run_id = new_uuid()
    started_at = utc_now()
    graph = build_quality_war_room_graph(db)
    graph.invoke(
        {
            "run_id": run_id,
            "draft_id": draft_id,
            "warnings": [],
            "errors": [],
            "iteration_count": 1,
            "max_iterations": MAX_SPECIALIST_PASSES,
            "model_metadata": {"provider": PROVIDER_NAME, "model": MODEL_NAME},
            "events": [],
            "started_at": started_at,
            "completed_at": None,
        }
    )
    return run_id
