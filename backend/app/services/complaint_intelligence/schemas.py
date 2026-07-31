from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime

DuplicateClassification = Literal[
    "LIKELY_EXACT_DUPLICATE",
    "POSSIBLE_DUPLICATE",
    "RECURRENCE_SIGNAL",
    "RELATED_QUALITY_SIGNAL",
    "UNRELATED",
]


class IntelligenceRunRequest(BaseModel):
    created_by: str | None = Field(default="Demo User", max_length=150)


class DuplicateCandidateResult(BaseModel):
    candidate_complaint_id: str
    complaint_number: str
    classification: DuplicateClassification
    total_score: int
    reasons: list[str] = Field(default_factory=list)
    matching_fields: list[str] = Field(default_factory=list)
    contradicting_fields: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    date_distance_days: int | None = None
    text_similarity: str
    recommended_user_action: str


class RecurrenceSignal(BaseModel):
    signal_type: str
    description: str
    evidence_references: list[str] = Field(default_factory=list)
    limitation: str


class DuplicateAnalysisResult(BaseModel):
    run_id: str
    draft_id: str
    candidates: list[DuplicateCandidateResult]
    recurrence_signals: list[RecurrenceSignal]
    limitations: list[str]


class DuplicateAnalysisRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str
    result_json: dict
    status: str
    created_at: UTCDateTime
    created_by: str | None = None
