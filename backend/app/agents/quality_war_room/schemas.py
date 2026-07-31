from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime


class QualityWarRoomRunRequest(BaseModel):
    created_by: str | None = Field(default="Demo User", max_length=150)


class SpecialistOutput(BaseModel):
    agent_name: str
    status: Literal["COMPLETE", "FAILED", "UNAVAILABLE"] = "COMPLETE"
    concise_findings: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    immediate_considerations: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    confidence: str = "LOW"
    limitations: list[str] = Field(default_factory=list)


class AuditorOutput(BaseModel):
    accepted_findings: list[str] = Field(default_factory=list)
    challenged_findings: list[str] = Field(default_factory=list)
    rejected_claims: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    contradiction_findings: list[str] = Field(default_factory=list)
    specialist_revision_requests: dict[str, list[str]] = Field(default_factory=dict)
    compliance_warnings: list[str] = Field(default_factory=list)


class ConsensusOutput(BaseModel):
    suggested_severity: str = "UNDETERMINED"
    suggested_priority: str = "UNDETERMINED"
    recommended_routes: list[str] = Field(default_factory=list)
    immediate_containment_considerations: list[str] = Field(default_factory=list)
    investigation_priorities: list[str] = Field(default_factory=list)
    root_cause_hypotheses: list[str] = Field(default_factory=list)
    confirmation_tests: list[str] = Field(default_factory=list)
    CAPA_considerations: dict[str, list[str]] = Field(default_factory=dict)
    agent_agreements: list[str] = Field(default_factory=list)
    agent_disagreements: list[str] = Field(default_factory=list)
    rejected_unsupported_claims: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    human_approval_required: bool = True


class WarRoomEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    event_type: str
    agent_name: str | None = None
    status: str
    concise_message: str
    evidence_ids_json: dict | None = None
    created_at: UTCDateTime


class QualityWarRoomRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str
    status: str
    iteration_count: int
    specialist_outputs_json: dict
    auditor_output_json: dict
    consensus_json: dict
    provider: str | None = None
    model: str | None = None
    started_at: UTCDateTime
    completed_at: UTCDateTime | None = None
    error_summary: str | None = None
    events: list[WarRoomEventResponse] = Field(default_factory=list)


class QualityWarRoomRunStartedResponse(BaseModel):
    run_id: str
    status: str
