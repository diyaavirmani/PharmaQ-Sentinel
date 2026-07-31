from __future__ import annotations

from app.core.exceptions import PharmaQSentinelError


class LLMGatewayError(PharmaQSentinelError):
    """Base error for server-side LLM gateway failures."""

    def __init__(self, message: str, *, status_code: int = 503) -> None:
        super().__init__(message, status_code=status_code)


class LLMConfigurationError(LLMGatewayError):
    def __init__(self, message: str = "AI service is not configured") -> None:
        super().__init__(message, status_code=503)


class LLMAuthenticationError(LLMGatewayError):
    def __init__(self) -> None:
        super().__init__("AI provider authentication failed", status_code=503)


class LLMRateLimitError(LLMGatewayError):
    def __init__(self) -> None:
        super().__init__("AI provider rate limit reached", status_code=429)


class LLMTimeoutError(LLMGatewayError):
    def __init__(self) -> None:
        super().__init__("AI provider request timed out", status_code=504)


class LLMInvalidRequestError(LLMGatewayError):
    def __init__(self, message: str = "AI provider rejected the request") -> None:
        super().__init__(message, status_code=422)


class LLMModelNotFoundError(LLMGatewayError):
    def __init__(self) -> None:
        super().__init__("Configured AI model is unavailable", status_code=503)


class LLMProviderUnavailableError(LLMGatewayError):
    def __init__(self) -> None:
        super().__init__("AI provider is unavailable", status_code=503)


class LLMStructuredOutputError(LLMGatewayError):
    def __init__(self, message: str = "AI provider returned invalid structured output") -> None:
        super().__init__(message, status_code=502)
