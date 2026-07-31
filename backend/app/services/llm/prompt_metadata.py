from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PromptMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt_name: str = Field(min_length=1, max_length=150)
    prompt_version: str = Field(min_length=1, max_length=50)
    tool_name: str = Field(min_length=1, max_length=150)
    date_introduced: date
    schema_name: str = Field(min_length=1, max_length=150)


PROMPT_REGISTRY: dict[str, PromptMetadata] = {}


def register_prompt_metadata(metadata: PromptMetadata) -> None:
    registry_key = f"{metadata.prompt_name}:{metadata.prompt_version}"
    PROMPT_REGISTRY[registry_key] = metadata


def get_prompt_metadata(prompt_name: str, prompt_version: str) -> PromptMetadata | None:
    return PROMPT_REGISTRY.get(f"{prompt_name}:{prompt_version}")
