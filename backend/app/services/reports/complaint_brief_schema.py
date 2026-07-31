from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime

INSPECTION_BRIEF_DISCLAIMER = (
    "AI-generated extraction, classifications and recommendations require review and approval by "
    "authorised quality personnel. This demonstration report is not a regulatory submission and "
    "does not itself establish regulatory compliance."
)


class BriefField(BaseModel):
    label: str
    value: Any = None


class SourceDocumentReference(BaseModel):
    original_filename: str
    mime_type: str
    checksum: str
    upload_date: str | None = None


class EvidenceReference(BaseModel):
    field_name: str
    current_value: Any = None
    source_type: str
    source_excerpt: str | None = None
    page_number: int | None = None
    confidence: str | None = None
    user_corrected: bool = False
    created_at: str | None = None


class ReportSection(BaseModel):
    title: str
    fields: list[BriefField] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ComplaintBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    title: str
    disclaimer: str
    complaint_id: str
    complaint_number: str
    version_number: int
    document_identifier: str
    generated_at: UTCDateTime
    snapshot_checksum: str
    report_checksum: str
    source_documents: list[SourceDocumentReference]
    field_evidence: list[EvidenceReference]
    user_corrections: list[dict[str, Any]]
    sections: list[ReportSection]
    limitations: list[str]
