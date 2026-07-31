from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from app.services.documents.schemas import DocumentTextResult


class DocumentParser(ABC):
    document_type: ClassVar[str]
    supported_mime_types: ClassVar[set[str]]

    @abstractmethod
    def parse(self, path: Path) -> DocumentTextResult:
        raise NotImplementedError
