from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from app.core.exceptions import PharmaQSentinelError
from app.services.documents.base import DocumentParser
from app.services.documents.schemas import DocumentSegment, DocumentTextResult


class TextDocumentParser(DocumentParser):
    document_type: ClassVar[str] = "TXT"
    supported_mime_types: ClassVar[set[str]] = {"text/plain"}

    def parse(self, path: Path) -> DocumentTextResult:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise PharmaQSentinelError("TXT file must be valid UTF-8", status_code=422) from exc

        segments: list[DocumentSegment] = []
        offset = 0
        for index, paragraph in enumerate((part.strip() for part in text.splitlines()), start=1):
            if not paragraph:
                offset += 1
                continue
            start = text.find(paragraph, offset)
            if start < 0:
                start = offset
            end = start + len(paragraph)
            segments.append(
                DocumentSegment(
                    segment_id=f"txt-p{index}",
                    paragraph_index=index,
                    text=paragraph,
                    start_offset=start,
                    end_offset=end,
                )
            )
            offset = end
        return DocumentTextResult(
            document_type=self.document_type,
            detected_mime_type="text/plain",
            text=text,
            segments=segments,
            metadata={"line_count": len(text.splitlines())},
        )
