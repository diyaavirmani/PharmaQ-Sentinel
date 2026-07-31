from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from app.services.llm.schemas import LLMRequestContext, StructuredLLMResult, TextLLMResult

TStructured = TypeVar("TStructured", bound=BaseModel)


class BaseLLMGateway(ABC):
    @abstractmethod
    def generate_structured(
        self,
        *,
        system_instructions: str,
        user_input: str,
        response_schema: type[TStructured],
        request_context: LLMRequestContext,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> StructuredLLMResult[TStructured]:
        raise NotImplementedError

    @abstractmethod
    def generate_text(
        self,
        *,
        system_instructions: str,
        user_input: str,
        request_context: LLMRequestContext,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> TextLLMResult:
        raise NotImplementedError
