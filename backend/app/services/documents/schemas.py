from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentSegment(BaseModel):
    segment_id: str
    page_number: int | None = None
    paragraph_index: int | None = None
    text: str
    start_offset: int
    end_offset: int


class DocumentTextResult(BaseModel):
    document_type: str
    detected_mime_type: str
    text: str
    segments: list[DocumentSegment] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
