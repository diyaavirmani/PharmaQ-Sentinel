from __future__ import annotations

from app.core.exceptions import PharmaQSentinelError
from app.services.documents.base import DocumentParser
from app.services.documents.docx_parser import DocxDocumentParser
from app.services.documents.email_parser import EmailDocumentParser
from app.services.documents.pdf_parser import PdfDocumentParser
from app.services.documents.text_parser import TextDocumentParser


class DocumentParserRegistry:
    def __init__(self) -> None:
        self.parsers: list[DocumentParser] = [
            PdfDocumentParser(),
            DocxDocumentParser(),
            TextDocumentParser(),
            EmailDocumentParser(),
        ]

    def get_parser(self, mime_type: str) -> DocumentParser:
        for parser in self.parsers:
            if mime_type in parser.supported_mime_types:
                return parser
        raise PharmaQSentinelError("No parser is available for this document type", status_code=422)
