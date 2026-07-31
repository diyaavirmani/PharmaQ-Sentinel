from __future__ import annotations

from decimal import Decimal
from typing import Literal

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.llm import LLMRequestContext, OpenAIModelGateway
from app.services.llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMStructuredOutputError,
    LLMTimeoutError,
)
from app.services.llm.response_parser import parse_json_text_as_model


class DemoStructuredOutput(BaseModel):
    severity: Literal["CRITICAL", "MAJOR", "MINOR", "UNDETERMINED"]
    confidence: Decimal = Field(ge=0, le=1)
    summary: str


class FakeResponse:
    def __init__(
        self,
        *,
        output_parsed: object | None = None,
        output_text: str | None = None,
        usage: object | None = None,
        response_id: str = "resp_test",
        model: str = "gpt-test-actual",
    ) -> None:
        self.id = response_id
        self.model = model
        self.output_parsed = output_parsed
        self.output_text = output_text
        self.usage = usage


class FakeResponsesResource:
    def __init__(self, *, parse_results: list[object] | None = None, create_results: list[object] | None = None) -> None:
        self.parse_results = parse_results or []
        self.create_results = create_results or []
        self.parse_calls: list[dict[str, object]] = []
        self.create_calls: list[dict[str, object]] = []

    def parse(self, **kwargs: object) -> object:
        self.parse_calls.append(kwargs)
        result = self.parse_results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def create(self, **kwargs: object) -> object:
        self.create_calls.append(kwargs)
        result = self.create_results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class FakeOpenAIClient:
    def __init__(self, responses: FakeResponsesResource) -> None:
        self.responses = responses


def settings_with_openai(**overrides: object) -> Settings:
    values = {
        "OPENAI_API_KEY": "sk-test-secret",
        "OPENAI_MODEL": "gpt-test",
        "OPENAI_MAX_RETRIES": 2,
        "OPENAI_TIMEOUT_SECONDS": 12,
        "OPENAI_MAX_OUTPUT_TOKENS": 3000,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def request_context(**overrides: object) -> LLMRequestContext:
    values = {
        "request_id": "req-test",
        "draft_id": "00000000-0000-0000-0000-000000000001",
        "thread_id": "thread-test",
        "tool_name": "gateway_unit_test",
        "purpose": "Unit test",
        "actor_identifier": "test-user",
        "prompt_version": "test-v1",
        "contains_sensitive_information": True,
        "metadata": {"source": "unit"},
    }
    values.update(overrides)
    return LLMRequestContext(**values)


def gateway_with_responses(responses: FakeResponsesResource, settings: Settings | None = None) -> OpenAIModelGateway:
    return OpenAIModelGateway(
        settings=settings or settings_with_openai(),
        client=FakeOpenAIClient(responses),
        sleeper=lambda _seconds: None,
    )


def timeout_error() -> APITimeoutError:
    return APITimeoutError(httpx.Request("POST", "https://api.openai.com/v1/responses"))


def connection_error() -> APIConnectionError:
    return APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
    )


def response_error(error_type: type[Exception], status_code: int) -> Exception:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code, request=request)
    return error_type("provider error sk-test-secret", response=response, body=None)


def valid_response(**overrides: object) -> FakeResponse:
    output = DemoStructuredOutput(
        severity="MINOR",
        confidence=Decimal("0.7500"),
        summary="Validated structured output",
    )
    values: dict[str, object] = {
        "output_parsed": output,
        "usage": {"input_tokens": 10, "output_tokens": 8, "total_tokens": 18},
    }
    values.update(overrides)
    return FakeResponse(**values)


def test_valid_structured_response() -> None:
    responses = FakeResponsesResource(parse_results=[valid_response()])
    result = gateway_with_responses(responses).generate_structured(
        system_instructions="Return structured output.",
        user_input="Use safe demo input.",
        response_schema=DemoStructuredOutput,
        request_context=request_context(),
    )

    assert result.provider == "openai"
    assert result.requested_model == "gpt-test"
    assert result.actual_model == "gpt-test-actual"
    assert result.parsed_output.severity == "MINOR"
    assert result.usage.total_tokens == 18


def test_pydantic_schema_validation_rejects_unknown_enum_and_numeric_range() -> None:
    with pytest.raises(LLMStructuredOutputError):
        parse_json_text_as_model(
            '{"severity": "INVALID", "confidence": "1.5000", "summary": "bad"}',
            DemoStructuredOutput,
        )


def test_invalid_structured_response_rejected_after_repair_attempt() -> None:
    responses = FakeResponsesResource(
        parse_results=[
            FakeResponse(output_text='{"severity": "INVALID"}'),
            FakeResponse(output_text='{"still": "bad"}'),
        ]
    )

    with pytest.raises(LLMStructuredOutputError):
        gateway_with_responses(responses).generate_structured(
            system_instructions="Return structured output.",
            user_input="Use safe demo input.",
            response_schema=DemoStructuredOutput,
            request_context=request_context(),
        )

    assert len(responses.parse_calls) == 2


def test_one_schema_repair_retry() -> None:
    responses = FakeResponsesResource(
        parse_results=[
            FakeResponse(output_text='{"severity": "INVALID"}'),
            FakeResponse(
                output_text='{"severity": "MAJOR", "confidence": "0.9000", "summary": "repaired"}',
                usage=None,
            ),
        ]
    )

    result = gateway_with_responses(responses).generate_structured(
        system_instructions="Return structured output.",
        user_input="Use safe demo input.",
        response_schema=DemoStructuredOutput,
        request_context=request_context(),
    )

    assert result.parsed_output.severity == "MAJOR"
    assert result.retry_count == 1
    assert "Token usage metadata unavailable" in result.warnings
    assert "Return one strict JSON object" in responses.parse_calls[1]["instructions"]


def test_permanent_malformed_output_rejected() -> None:
    responses = FakeResponsesResource(
        parse_results=[
            FakeResponse(output_text="```json\nnot-json\n```"),
            FakeResponse(output_text="```json\nstill-not-json\n```"),
        ]
    )

    with pytest.raises(LLMStructuredOutputError):
        gateway_with_responses(responses).generate_structured(
            system_instructions="Return structured output.",
            user_input="Use safe demo input.",
            response_schema=DemoStructuredOutput,
            request_context=request_context(),
        )


def test_timeout_handling() -> None:
    responses = FakeResponsesResource(parse_results=[timeout_error()])
    gateway = gateway_with_responses(responses, settings_with_openai(OPENAI_MAX_RETRIES=0))

    with pytest.raises(LLMTimeoutError):
        gateway.generate_structured(
            system_instructions="Return structured output.",
            user_input="Use safe demo input.",
            response_schema=DemoStructuredOutput,
            request_context=request_context(),
        )


def test_temporary_retry() -> None:
    responses = FakeResponsesResource(parse_results=[connection_error(), valid_response()])

    result = gateway_with_responses(responses).generate_structured(
        system_instructions="Return structured output.",
        user_input="Use safe demo input.",
        response_schema=DemoStructuredOutput,
        request_context=request_context(),
    )

    assert result.retry_count == 1
    assert len(responses.parse_calls) == 2


def test_authentication_errors_are_not_retried() -> None:
    responses = FakeResponsesResource(
        parse_results=[response_error(AuthenticationError, 401)],
    )

    with pytest.raises(LLMAuthenticationError):
        gateway_with_responses(responses).generate_structured(
            system_instructions="Return structured output.",
            user_input="Use safe demo input.",
            response_schema=DemoStructuredOutput,
            request_context=request_context(),
        )

    assert len(responses.parse_calls) == 1


def test_rate_limit_retry() -> None:
    responses = FakeResponsesResource(
        parse_results=[response_error(RateLimitError, 429), valid_response()],
    )

    result = gateway_with_responses(responses).generate_structured(
        system_instructions="Return structured output.",
        user_input="Use safe demo input.",
        response_schema=DemoStructuredOutput,
        request_context=request_context(),
    )

    assert result.retry_count == 1


def test_missing_api_key() -> None:
    responses = FakeResponsesResource(parse_results=[valid_response()])

    with pytest.raises(LLMConfigurationError):
        gateway_with_responses(responses, settings_with_openai(OPENAI_API_KEY="")).generate_structured(
            system_instructions="Return structured output.",
            user_input="Use safe demo input.",
            response_schema=DemoStructuredOutput,
            request_context=request_context(),
        )


def test_missing_model() -> None:
    responses = FakeResponsesResource(parse_results=[valid_response()])

    with pytest.raises(LLMConfigurationError):
        gateway_with_responses(responses, settings_with_openai(OPENAI_MODEL="")).generate_structured(
            system_instructions="Return structured output.",
            user_input="Use safe demo input.",
            response_schema=DemoStructuredOutput,
            request_context=request_context(),
        )


def test_api_key_does_not_appear_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    responses = FakeResponsesResource(parse_results=[response_error(AuthenticationError, 401)])

    with caplog.at_level("WARNING"), pytest.raises(LLMAuthenticationError):
        gateway_with_responses(responses).generate_structured(
            system_instructions="Return structured output.",
            user_input="sk-test-secret must not be logged",
            response_schema=DemoStructuredOutput,
            request_context=request_context(),
        )

    assert "sk-test-secret" not in caplog.text


def test_api_key_does_not_appear_in_status_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    get_settings.cache_clear()

    response = TestClient(create_app()).get("/api/v1/ai/status")

    assert response.status_code == 200
    assert "sk-test-secret" not in response.text
    assert response.json()["model"] == "gpt-test"


def test_complete_prompts_are_not_logged_by_default(caplog: pytest.LogCaptureFixture) -> None:
    responses = FakeResponsesResource(parse_results=[valid_response()])
    prompt_text = "Full demo complaint text that should not be logged by default."

    with caplog.at_level("INFO"):
        gateway_with_responses(responses).generate_structured(
            system_instructions="Return structured output.",
            user_input=prompt_text,
            response_schema=DemoStructuredOutput,
            request_context=request_context(),
        )

    assert prompt_text not in caplog.text


def test_application_starts_without_ai_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "")
    get_settings.cache_clear()

    response = TestClient(create_app()).get("/api/v1/ai/status")

    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert response.json()["available"] is False


def test_development_test_endpoint_is_unavailable_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("OPENAI_ENABLE_TEST_CONNECTION", "true")
    get_settings.cache_clear()

    response = TestClient(create_app()).post("/api/v1/ai/test-connection")

    assert response.status_code == 404


def test_request_metadata_returned_correctly() -> None:
    responses = FakeResponsesResource(parse_results=[valid_response()])
    context = request_context(metadata={"source": "unit", "safe_flag": True})

    gateway_with_responses(responses).generate_structured(
        system_instructions="Return structured output.",
        user_input="Use safe demo input.",
        response_schema=DemoStructuredOutput,
        request_context=context,
    )

    metadata = responses.parse_calls[0]["metadata"]
    assert metadata["request_id"] == "req-test"
    assert metadata["draft_id"] == "00000000-0000-0000-0000-000000000001"
    assert metadata["ctx_source"] == "unit"
    assert metadata["ctx_safe_flag"] == "True"


def test_token_metadata_handled_when_missing() -> None:
    responses = FakeResponsesResource(parse_results=[valid_response(usage=None)])

    result = gateway_with_responses(responses).generate_structured(
        system_instructions="Return structured output.",
        user_input="Use safe demo input.",
        response_schema=DemoStructuredOutput,
        request_context=request_context(),
    )

    assert result.usage.input_tokens is None
    assert result.usage.output_tokens is None
    assert result.usage.total_tokens is None
    assert "Token usage metadata unavailable" in result.warnings


def test_context_rejects_secret_metadata() -> None:
    with pytest.raises(ValidationError):
        request_context(metadata={"api_key": "sk-test-secret"})
