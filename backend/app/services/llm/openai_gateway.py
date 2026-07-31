from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.models.base import utc_now
from app.services.llm.base import BaseLLMGateway
from app.services.llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMGatewayError,
    LLMInvalidRequestError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
)
from app.services.llm.response_parser import extract_output_text, parse_json_text_as_model
from app.services.llm.retry_policy import RetryPolicy
from app.services.llm.schemas import (
    AIStatusResponse,
    LLMRequestContext,
    LLMUsage,
    StructuredLLMResult,
    TextLLMResult,
)

logger = logging.getLogger(__name__)
TStructured = TypeVar("TStructured", bound=BaseModel)

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
LONG_IDENTIFIER_PATTERN = re.compile(r"\b[A-Z0-9][A-Z0-9_-]{5,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")


class ProviderStatusCache:
    def __init__(self) -> None:
        self.available: bool | None = None
        self.last_checked_at: datetime | None = None
        self.message: str | None = None

    def update(self, *, available: bool, message: str) -> None:
        self.available = available
        self.message = message
        self.last_checked_at = utc_now()


provider_status_cache = ProviderStatusCache()


def build_ai_status(settings: Settings | None = None) -> AIStatusResponse:
    resolved_settings = settings or get_settings()
    api_key_configured = bool(resolved_settings.openai_api_key.get_secret_value())
    model_configured = bool(resolved_settings.openai_model)
    provider_configured = resolved_settings.llm_provider == "openai"
    configured = provider_configured and api_key_configured and model_configured

    if not configured:
        return AIStatusResponse(
            provider="openai",
            configured=False,
            available=False,
            model_configured=model_configured,
            model=resolved_settings.openai_model or None,
            last_checked_at=provider_status_cache.last_checked_at or utc_now(),
            message="AI service is not configured",
        )

    if provider_status_cache.available is False:
        return AIStatusResponse(
            provider="openai",
            configured=True,
            available=False,
            model_configured=True,
            model=resolved_settings.openai_model,
            last_checked_at=provider_status_cache.last_checked_at or utc_now(),
            message=provider_status_cache.message or "AI service unavailable",
        )

    return AIStatusResponse(
        provider="openai",
        configured=True,
        available=True,
        model_configured=True,
        model=resolved_settings.openai_model,
        last_checked_at=provider_status_cache.last_checked_at or utc_now(),
        message=provider_status_cache.message or "AI service available",
    )


class OpenAIModelGateway(BaseLLMGateway):
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or get_settings()
        self.retry_policy = RetryPolicy(max_retries=self.settings.openai_max_retries)
        self._provided_client = client
        self._client: Any | None = client
        self._sleeper = sleeper

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
        if not isinstance(response_schema, type) or not issubclass(response_schema, BaseModel):
            raise LLMInvalidRequestError("Structured output schema must be a Pydantic BaseModel type")

        model = self._configured_model()
        requested_temperature = self.settings.openai_temperature if temperature is None else temperature
        requested_max_tokens = (
            self.settings.openai_max_output_tokens if max_output_tokens is None else max_output_tokens
        )
        warnings: list[str] = []

        def make_request(repair_instruction: str | None = None) -> object:
            instructions = system_instructions
            input_text = user_input
            if repair_instruction:
                instructions = f"{system_instructions}\n\n{repair_instruction}"
                input_text = f"{user_input}\n\nReturn corrected JSON only."

            if hasattr(self.client.responses, "parse"):
                return self.client.responses.parse(
                    model=model,
                    instructions=instructions,
                    input=input_text,
                    text_format=response_schema,
                    temperature=requested_temperature,
                    max_output_tokens=requested_max_tokens,
                    metadata=self._safe_openai_metadata(request_context),
                    timeout=self.settings.openai_timeout_seconds,
                )

            warnings.append("SDK parse helper unavailable; used JSON text fallback")
            return self.client.responses.create(
                model=model,
                instructions=instructions,
                input=input_text,
                temperature=requested_temperature,
                max_output_tokens=requested_max_tokens,
                metadata=self._safe_openai_metadata(request_context),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": response_schema.__name__,
                        "strict": True,
                        "schema": response_schema.model_json_schema(),
                    }
                },
                timeout=self.settings.openai_timeout_seconds,
            )

        started_at = time.perf_counter()
        response, retry_count = self._execute_with_retries(
            operation=lambda: make_request(None),
            request_context=request_context,
            model=model,
        )

        try:
            parsed_output = self._parse_structured_response(response, response_schema)
        except LLMStructuredOutputError:
            repair_instruction = (
                "The previous response did not validate against the required Pydantic schema. "
                "Return one strict JSON object that conforms exactly to the schema. Do not add markdown."
            )
            repair_response, repair_retries = self._execute_with_retries(
                operation=lambda: make_request(repair_instruction),
                request_context=request_context,
                model=model,
            )
            retry_count += 1 + repair_retries
            parsed_output = self._parse_structured_response(repair_response, response_schema)
            response = repair_response

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        result = StructuredLLMResult(
            provider="openai",
            requested_model=model,
            actual_model=self._actual_model(response, model),
            response_id=getattr(response, "id", None),
            prompt_version=request_context.prompt_version,
            usage=self._usage_from_response(response, warnings),
            latency_ms=latency_ms,
            retry_count=retry_count,
            created_at=utc_now(),
            parsed_output=parsed_output,
            warnings=warnings,
        )
        self._log_success(request_context, model, result.actual_model, latency_ms, retry_count)
        return result

    def generate_text(
        self,
        *,
        system_instructions: str,
        user_input: str,
        request_context: LLMRequestContext,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> TextLLMResult:
        model = self._configured_model()
        requested_temperature = self.settings.openai_temperature if temperature is None else temperature
        requested_max_tokens = (
            self.settings.openai_max_output_tokens if max_output_tokens is None else max_output_tokens
        )
        warnings: list[str] = []
        started_at = time.perf_counter()

        response, retry_count = self._execute_with_retries(
            operation=lambda: self.client.responses.create(
                model=model,
                instructions=system_instructions,
                input=user_input,
                temperature=requested_temperature,
                max_output_tokens=requested_max_tokens,
                metadata=self._safe_openai_metadata(request_context),
                timeout=self.settings.openai_timeout_seconds,
            ),
            request_context=request_context,
            model=model,
        )

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        output_text = extract_output_text(response)
        result = TextLLMResult(
            provider="openai",
            requested_model=model,
            actual_model=self._actual_model(response, model),
            response_id=getattr(response, "id", None),
            prompt_version=request_context.prompt_version,
            usage=self._usage_from_response(response, warnings),
            latency_ms=latency_ms,
            retry_count=retry_count,
            created_at=utc_now(),
            output_text=output_text,
            warnings=warnings,
        )
        self._log_success(request_context, model, result.actual_model, latency_ms, retry_count)
        return result

    @property
    def client(self) -> Any:
        if self._client is None:
            api_key = self.settings.openai_api_key.get_secret_value()
            self._client = OpenAI(
                api_key=api_key,
                timeout=self.settings.openai_timeout_seconds,
                max_retries=0,
            )
        return self._client

    def _configured_model(self) -> str:
        if self.settings.llm_provider != "openai":
            raise LLMConfigurationError("Configured LLM provider is not supported")
        if not self.settings.openai_api_key.get_secret_value():
            raise LLMConfigurationError("OpenAI API key is not configured")
        if not self.settings.openai_model:
            raise LLMConfigurationError("OpenAI model is not configured")
        return self.settings.openai_model

    def _execute_with_retries(
        self,
        *,
        operation: Callable[[], object],
        request_context: LLMRequestContext,
        model: str,
    ) -> tuple[object, int]:
        retry_count = 0
        while True:
            try:
                return operation(), retry_count
            except Exception as exc:
                mapped_error = self._map_provider_error(exc)
                if not self.retry_policy.should_retry(exc) or retry_count >= self.retry_policy.max_retries:
                    self._log_failure(request_context, model, mapped_error, retry_count)
                    raise mapped_error from exc

                retry_count += 1
                self._sleeper(self.retry_policy.delay_seconds(retry_count))

    def _parse_structured_response(
        self,
        response: object,
        response_schema: type[TStructured],
    ) -> TStructured:
        parsed_output = getattr(response, "output_parsed", None)
        try:
            if parsed_output is not None:
                return response_schema.model_validate(parsed_output)
        except ValidationError as exc:
            raise LLMStructuredOutputError("AI provider returned invalid structured output") from exc

        output_text = extract_output_text(response)
        return parse_json_text_as_model(output_text, response_schema)

    def _map_provider_error(self, exc: Exception) -> LLMGatewayError:
        if isinstance(exc, AuthenticationError | PermissionDeniedError):
            return LLMAuthenticationError()
        if isinstance(exc, APITimeoutError):
            return LLMTimeoutError()
        if isinstance(exc, RateLimitError):
            return LLMRateLimitError()
        if isinstance(exc, NotFoundError):
            return LLMModelNotFoundError()
        if isinstance(exc, BadRequestError):
            if "model" in str(exc).lower():
                return LLMModelNotFoundError()
            return LLMInvalidRequestError()
        if isinstance(exc, APIConnectionError):
            return LLMProviderUnavailableError()
        if isinstance(exc, APIStatusError):
            return LLMProviderUnavailableError()
        if isinstance(exc, LLMGatewayError):
            return exc
        return LLMProviderUnavailableError()

    def _safe_openai_metadata(self, request_context: LLMRequestContext) -> dict[str, str]:
        metadata = {
            "request_id": request_context.request_id,
            "tool_name": request_context.tool_name,
            "purpose": request_context.purpose,
            "prompt_version": request_context.prompt_version,
        }
        if request_context.draft_id:
            metadata["draft_id"] = request_context.draft_id
        if request_context.thread_id:
            metadata["thread_id"] = request_context.thread_id
        if request_context.actor_identifier:
            metadata["actor_identifier"] = request_context.actor_identifier

        for key, value in request_context.metadata.items():
            if value is not None:
                metadata[f"ctx_{key}"] = str(value)[:500]
        return metadata

    def _usage_from_response(self, response: object, warnings: list[str]) -> LLMUsage:
        usage = getattr(response, "usage", None)
        if usage is None:
            warnings.append("Token usage metadata unavailable")
            return LLMUsage()

        input_tokens = self._usage_value(usage, "input_tokens", "prompt_tokens")
        output_tokens = self._usage_value(usage, "output_tokens", "completion_tokens")
        total_tokens = self._usage_value(usage, "total_tokens")
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    def _usage_value(self, usage: object, *names: str) -> int | None:
        for name in names:
            if isinstance(usage, dict) and isinstance(usage.get(name), int):
                return usage[name]
            value = getattr(usage, name, None)
            if isinstance(value, int):
                return value
        return None

    def _actual_model(self, response: object, requested_model: str) -> str:
        actual_model = getattr(response, "model", None)
        return actual_model if isinstance(actual_model, str) and actual_model else requested_model

    def _log_success(
        self,
        request_context: LLMRequestContext,
        requested_model: str,
        actual_model: str,
        latency_ms: int,
        retry_count: int,
    ) -> None:
        self._log_prompt_excerpt(request_context)
        logger.info(
            "LLM request succeeded request_id=%s tool=%s provider=openai requested_model=%s "
            "actual_model=%s latency_ms=%s retry_count=%s",
            request_context.request_id,
            request_context.tool_name,
            requested_model,
            actual_model,
            latency_ms,
            retry_count,
        )

    def _log_failure(
        self,
        request_context: LLMRequestContext,
        requested_model: str,
        error: LLMGatewayError,
        retry_count: int,
    ) -> None:
        logger.warning(
            "LLM request failed request_id=%s tool=%s provider=openai requested_model=%s "
            "failure_type=%s retry_count=%s",
            request_context.request_id,
            request_context.tool_name,
            requested_model,
            error.__class__.__name__,
            retry_count,
        )

    def _log_prompt_excerpt(self, request_context: LLMRequestContext) -> None:
        if self.settings.app_env != "development" or not self.settings.openai_log_prompts:
            return

        logger.debug(
            "Development-only prompt logging enabled request_id=%s metadata=%s",
            request_context.request_id,
            self._redacted_metadata(request_context.metadata),
        )

    def _redacted_metadata(self, metadata: dict[str, object]) -> dict[str, object]:
        redacted: dict[str, object] = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                redacted[key] = redact_development_text(value)
            else:
                redacted[key] = value
        return redacted


def redact_development_text(text: str) -> str:
    redacted = EMAIL_PATTERN.sub("[redacted-email]", text)
    redacted = PHONE_PATTERN.sub("[redacted-phone]", redacted)
    return LONG_IDENTIFIER_PATTERN.sub("[redacted-id]", redacted)
