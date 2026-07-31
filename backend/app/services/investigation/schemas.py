from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime


class PlaybookStep(BaseModel):
    id: str
    title: str
    rationale: str
    evidence_references: list[str] = Field(default_factory=list)
    owner_hint: str
    limitation: str


class InvestigationPlaybookResult(BaseModel):
    run_id: str
    draft_id: str
    category: str
    immediate_containment: list[PlaybookStep]
    investigation_checklist: list[PlaybookStep]
    root_cause_hypotheses: list[PlaybookStep]
    CAPA_considerations: dict[str, list[PlaybookStep]]
    limitations: list[str]


class InvestigationPlaybookRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str
    playbook_json: dict
    status: str
    created_at: UTCDateTime
    created_by: str | None = None


class InvestigationReviewActionRequest(BaseModel):
    action_type: str = Field(max_length=80)
    target_type: str = Field(max_length=80)
    target_id: str | None = Field(default=None, max_length=150)
    run_id: str | None = Field(default=None, max_length=36)
    original_text: dict | None = None
    saved_text: str | None = None
    reason: str | None = Field(default=None, max_length=500)
    actor_identifier: str | None = Field(default="Demo QA User", max_length=150)


class InvestigationReviewActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str
    run_id: str | None = None
    action_type: str
    target_type: str
    target_id: str | None = None
    saved_text: str | None = None
    reason: str | None = None
    actor_identifier: str | None = None
    created_at: UTCDateTime
