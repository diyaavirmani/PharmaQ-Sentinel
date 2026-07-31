from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

SensitiveMetadataValue = str | int | float | bool | None
TParsed = TypeVar("TParsed", bound=BaseModel)

SENSITIVE_METADATA_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "database_url",
    "password",
    "secret",
    "token",
)


class LLMRequestContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=150)
    draft_id: str | None = Field(default=None, max_length=36)
    thread_id: str | None = Field(default=None, max_length=100)
    tool_name: str = Field(min_length=1, max_length=150)
    purpose: str = Field(min_length=1, max_length=250)
    actor_identifier: str | None = Field(default=None, max_length=150)
    prompt_version: str = Field(min_length=1, max_length=50)
    contains_sensitive_information: bool = True
    metadata: dict[str, SensitiveMetadataValue] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_secret_metadata(cls, value: dict[str, SensitiveMetadataValue]) -> dict[str, SensitiveMetadataValue]:
        for key, metadata_value in value.items():
            lowered = key.lower()
            if any(secret_part in lowered for secret_part in SENSITIVE_METADATA_KEY_PARTS):
                raise ValueError(f"metadata key is not allowed: {key}")
            if isinstance(metadata_value, str) and metadata_value.startswith(("sk-", "sess-")):
                raise ValueError(f"metadata value appears to contain a secret: {key}")
        return value


class LLMUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class StructuredLLMResult(BaseModel, Generic[TParsed]):
    provider: Literal["openai"]
    requested_model: str
    actual_model: str
    response_id: str | None
    prompt_version: str
    usage: LLMUsage
    latency_ms: int
    retry_count: int
    created_at: datetime
    parsed_output: TParsed
    warnings: list[str] = Field(default_factory=list)


class TextLLMResult(BaseModel):
    provider: Literal["openai"]
    requested_model: str
    actual_model: str
    response_id: str | None
    prompt_version: str
    usage: LLMUsage
    latency_ms: int
    retry_count: int
    created_at: datetime
    output_text: str
    warnings: list[str] = Field(default_factory=list)


class AIStatusResponse(BaseModel):
    provider: Literal["openai"]
    configured: bool
    available: bool
    model_configured: bool
    model: str | None
    last_checked_at: datetime
    message: str


class AITestConnectionResponse(BaseModel):
    provider: Literal["openai"]
    available: bool
    model: str | None
    response_id: str | None
    latency_ms: int | None
    message: str
