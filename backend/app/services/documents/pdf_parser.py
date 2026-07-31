from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import fitz

from app.core.exceptions import PharmaQSentinelError
from app.services.documents.base import DocumentParser
from app.services.documents.schemas import DocumentSegment, DocumentTextResult


class PdfDocumentParser(DocumentParser):
    document_type: ClassVar[str] = "PDF"
    supported_mime_types: ClassVar[set[str]] = {"application/pdf"}

    def parse(self, path: Path) -> DocumentTextResult:
        try:
            document = fitz.open(path)
        except Exception as exc:
            raise PharmaQSentinelError("Malformed PDF could not be parsed", status_code=422) from exc

        segments: list[DocumentSegment] = []
        text_parts: list[str] = []
        offset = 0
        for page_index, page in enumerate(document, start=1):
            blocks = page.get_text("blocks")
            for block_index, block in enumerate(blocks, start=1):
                block_text = " ".join(str(block[4]).split())
                if not block_text:
                    continue
                start = offset
                end = start + len(block_text)
                segments.append(
                    DocumentSegment(
                        segment_id=f"p{page_index}-b{block_index}",
                        page_number=page_index,
                        paragraph_index=block_index,
                        text=block_text,
                        start_offset=start,
                        end_offset=end,
                    )
                )
                text_parts.append(block_text)
                offset = end + 1

        warnings = []
        if not text_parts:
            warnings.append("PDF appears to be image-only; OCR is not enabled in this phase.")
        return DocumentTextResult(
            document_type=self.document_type,
            detected_mime_type="application/pdf",
            text="\n".join(text_parts),
            segments=segments,
            metadata={"page_count": document.page_count},
            warnings=warnings,
        )
