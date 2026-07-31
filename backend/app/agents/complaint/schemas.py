from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agents.complaint.constants import ComplaintAssistantIntent
from app.models.enums import Priority, ProductType, Severity
from app.schemas.common import UTCDateTime
from app.schemas.complaints import ComplaintDraftResponse


class ComplaintIntentClassification(BaseModel):
    intent: ComplaintAssistantIntent
    confidence: float = Field(ge=0, le=1)
    reason_summary: str = Field(max_length=300)
    clarification_required: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)


class ToolStubResult(BaseModel):
    implemented: Literal[False] = False
    tool_name: str
    safe_message: str
    proposed_patch: None = None
    changed_fields: list[str] = Field(default_factory=list)


class ComplaintFieldExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any | None = None
    original_text: str | None = Field(default=None, max_length=500)
    explicitly_stated: bool = False
    normalised: Any | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_excerpt: str | None = Field(default=None, max_length=1000)
    warning: str | None = Field(default=None, max_length=300)

    @field_validator("original_text", "source_excerpt", "warning", mode="before")
    @classmethod
    def empty_text_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ComplaintExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extracted_fields: dict[str, ComplaintFieldExtraction] = Field(default_factory=dict)
    complaint_classification: str | None = Field(default=None, max_length=150)
    detected_language: str | None = Field(default=None, max_length=80)
    product_type: ProductType | None = None
    possible_quality_defect: bool = False
    possible_adverse_event: bool = False
    possible_counterfeit: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    concise_summary: str | None = Field(default=None, max_length=800)


class ProvisionalRiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggested_severity: Severity
    suggested_priority: Priority
    patient_harm_level: str | None = Field(default=None, max_length=30)
    risk_rationale: str = Field(min_length=1, max_length=1500)
    potential_hazard: str | None = Field(default=None, max_length=1000)
    recommended_next_action: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)
    supporting_fields: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    requires_qa_confirmation: bool = True


class ComplaintEditOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(min_length=1, max_length=150)
    operation: Literal["SET", "CLEAR"]
    new_value: Any | None = None
    explicitly_requested: bool = False
    source_excerpt: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("field_name", "source_excerpt", "reason", mode="before")
    @classmethod
    def normalise_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.strip().split())
        return value


class ComplaintEditResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operations: list[ComplaintEditOperation] = Field(default_factory=list)
    no_op_fields: list[str] = Field(default_factory=list)
    ambiguous_requests: list[str] = Field(default_factory=list)
    clarification_required: bool = False
    clarification_question: str | None = Field(default=None, max_length=400)
    warnings: list[str] = Field(default_factory=list)
    concise_summary: str = Field(default="", max_length=800)


class DocumentFieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(min_length=1, max_length=150)
    value: Any | None = None
    attachment_id: str = Field(min_length=1, max_length=36)
    page_number: int | None = None
    paragraph_index: int | None = None
    source_excerpt: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)
    explicitly_stated: bool = True
    normalised: Any | None = None
    extraction_method: str = Field(default="DOCUMENT_EXTRACTION", max_length=150)


class DocumentComplaintExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str = Field(min_length=1, max_length=40)
    detected_language: str | None = Field(default=None, max_length=80)
    extracted_fields: dict[str, ComplaintFieldExtraction] = Field(default_factory=dict)
    evidence_by_field: list[DocumentFieldEvidence] = Field(default_factory=list)
    complaint_classification: str | None = Field(default=None, max_length=150)
    possible_safety_signals: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    extraction_confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    concise_summary: str | None = Field(default=None, max_length=800)


class ComplaintAssistantMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    attachment_id: str | None = Field(default=None, max_length=36)

    @field_validator("message")
    @classmethod
    def normalise_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        return stripped


class ComplaintMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str
    role: str
    message_text: str
    attachment_id: str | None = None
    created_at: UTCDateTime
    metadata_json: dict | None = None


class ComplaintAssistantMessageResponse(BaseModel):
    user_message: ComplaintMessageResponse
    assistant_message: ComplaintMessageResponse
    intent: ComplaintAssistantIntent
    tool_name: str | None
    draft: ComplaintDraftResponse
    changed_fields: list[str]
    warnings: list[str]
    clarification_required: bool


class ComplaintMessageListResponse(BaseModel):
    messages: list[ComplaintMessageResponse]
    limit: int
    offset: int
    next_offset: int | None
