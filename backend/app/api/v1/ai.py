from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header

from app.core.config import get_settings
from app.core.exceptions import PharmaQSentinelError
from app.services.llm import (
    AIStatusResponse,
    AITestConnectionResponse,
    LLMRequestContext,
    OpenAIModelGateway,
    build_ai_status,
)
from app.services.llm.openai_gateway import provider_status_cache

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status", response_model=AIStatusResponse)
def ai_status() -> AIStatusResponse:
    return build_ai_status()


@router.post("/test-connection", response_model=AITestConnectionResponse)
def test_ai_connection(
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> AITestConnectionResponse:
    settings = get_settings()
    if settings.app_env != "development" or not settings.openai_enable_test_connection_endpoint:
        raise PharmaQSentinelError("AI test connection endpoint is not enabled", status_code=404)

    request_context = LLMRequestContext(
        request_id=x_request_id or "development-ai-test",
        draft_id=None,
        thread_id=None,
        tool_name="ai_test_connection",
        purpose="Development-only OpenAI connectivity check",
        actor_identifier="system",
        prompt_version="ai-test-connection-v1",
        contains_sensitive_information=False,
        metadata={"development_only": True},
    )
    result = OpenAIModelGateway(settings=settings).generate_text(
        system_instructions="Return a short plain-text health acknowledgement. Do not include secrets.",
        user_input="Reply with: ok",
        request_context=request_context,
        temperature=0,
        max_output_tokens=8,
    )
    provider_status_cache.update(available=True, message="AI service available")
    return AITestConnectionResponse(
        provider="openai",
        available=True,
        model=result.actual_model,
        response_id=result.response_id,
        latency_ms=result.latency_ms,
        message="AI service available",
    )
