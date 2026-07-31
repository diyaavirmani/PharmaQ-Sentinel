from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DecimalString, UTCDateTime


class EvidenceStatus(str, Enum):
    EXPLICIT_SOURCE = "EXPLICIT_SOURCE"
    NORMALISED_SOURCE = "NORMALISED_SOURCE"
    AI_INFERENCE = "AI_INFERENCE"
    USER_CORRECTION = "USER_CORRECTION"
    SYSTEM_REFERENCE = "SYSTEM_REFERENCE"
    CONFLICTING_SOURCE = "CONFLICTING_SOURCE"
    SUPERSEDED = "SUPERSEDED"


class EvidenceSourceMessage(BaseModel):
    id: str
    role: str
    message_text: str
    created_at: UTCDateTime


class EvidenceSourceAttachment(BaseModel):
    id: str
    original_filename: str
    mime_type: str
    file_size: int
    sha256_checksum: str
    extraction_status: str
    created_at: UTCDateTime
    uploaded_by: str | None = None


class FieldEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str
    field_name: str
    field_value: dict[str, Any] | None = None
    display_value: Any = None
    evidence_type: str
    evidence_status: EvidenceStatus
    conflict_status: str
    active_reason: str | None = None
    source_message_id: str | None = None
    source_attachment_id: str | None = None
    source_message: EvidenceSourceMessage | None = None
    source_attachment: EvidenceSourceAttachment | None = None
    page_number: int | None = None
    paragraph_index: int | None = None
    source_excerpt: str | None = None
    confidence: DecimalString | None = None
    extraction_method: str | None = None
    is_explicit: bool
    is_normalised: bool
    is_inferred: bool
    is_active: bool
    provider_name: str | None = None
    actual_model: str | None = None
    created_at: UTCDateTime


class EvidenceConflictResponse(BaseModel):
    field_name: str
    is_critical: bool
    current_value: Any = None
    active_evidence_id: str | None = None
    conflicting_evidence_ids: list[str] = Field(default_factory=list)
    active_reason: str
    description: str


class FieldEvidenceListResponse(BaseModel):
    items: list[FieldEvidenceResponse]
    limit: int
    offset: int
    next_offset: int | None = None
    conflicts: list[EvidenceConflictResponse] = Field(default_factory=list)
    critical_conflicts_block_save: bool = False


class FieldEvidenceDetailResponse(BaseModel):
    field_name: str
    current_value: Any = None
    current_active_evidence: FieldEvidenceResponse | None = None
    evidence_history: list[FieldEvidenceResponse]
    conflicts: list[EvidenceConflictResponse] = Field(default_factory=list)
    critical_conflict_unresolved: bool = False


class TimelineEntryResponse(BaseModel):
    event_id: str
    event_type: str
    actor: str
    timestamp: UTCDateTime
    title: str
    description: str
    affected_fields: list[str] = Field(default_factory=list)
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    evidence_references: list[str] = Field(default_factory=list)
    attachment_references: list[str] = Field(default_factory=list)
    provider_name: str | None = None
    actual_model: str | None = None


class TimelineListResponse(BaseModel):
    items: list[TimelineEntryResponse]
    limit: int
    offset: int
    next_offset: int | None = None
