from __future__ import annotations

from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar

from app.core.exceptions import PharmaQSentinelError
from app.services.documents.base import DocumentParser
from app.services.documents.schemas import DocumentSegment, DocumentTextResult


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)


def html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return "\n".join(parser.parts)


class EmailDocumentParser(DocumentParser):
    document_type: ClassVar[str] = "EML"
    supported_mime_types: ClassVar[set[str]] = {"message/rfc822"}

    def parse(self, path: Path) -> DocumentTextResult:
        try:
            message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        except Exception as exc:
            raise PharmaQSentinelError("Malformed EML could not be parsed", status_code=422) from exc

        body_parts: list[str] = []
        warnings: list[str] = []
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                disposition = part.get_content_disposition()
                if disposition == "attachment":
                    if content_type == "text/plain":
                        body_parts.append(str(part.get_content()))
                    continue
                if content_type == "text/plain":
                    body_parts.append(str(part.get_content()))
                elif content_type == "text/html":
                    body_parts.append(html_to_text(str(part.get_content())))
        else:
            content_type = message.get_content_type()
            content = str(message.get_content())
            body_parts.append(html_to_text(content) if content_type == "text/html" else content)

        header_text = "\n".join(
            f"{label}: {message.get(label, '')}"
            for label in ("Subject", "From", "To", "Date")
            if message.get(label)
        )
        text = "\n".join(part for part in [header_text, *body_parts] if part.strip())
        if not text.strip():
            warnings.append("EML contained no extractable plain text.")

        segments: list[DocumentSegment] = []
        offset = 0
        for index, paragraph in enumerate((part.strip() for part in text.splitlines()), start=1):
            if not paragraph:
                continue
            start = text.find(paragraph, offset)
            if start < 0:
                start = offset
            end = start + len(paragraph)
            segments.append(
                DocumentSegment(
                    segment_id=f"eml-p{index}",
                    paragraph_index=index,
                    text=paragraph,
                    start_offset=start,
                    end_offset=end,
                )
            )
            offset = end

        return DocumentTextResult(
            document_type=self.document_type,
            detected_mime_type="message/rfc822",
            text=text,
            segments=segments,
            metadata={
                "subject": message.get("Subject"),
                "from": message.get("From"),
                "to": message.get("To"),
                "sent_date": message.get("Date"),
            },
            warnings=warnings,
        )
