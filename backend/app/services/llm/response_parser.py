from __future__ import annotations

import json
from json import JSONDecodeError
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.services.llm.exceptions import LLMStructuredOutputError

TParsed = TypeVar("TParsed", bound=BaseModel)


def strip_markdown_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```") or not stripped.endswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped

    opening = lines[0].strip().lower()
    if opening not in {"```", "```json"}:
        return stripped

    return "\n".join(lines[1:-1]).strip()


def parse_json_text_as_model(text: str, response_schema: type[TParsed]) -> TParsed:
    try:
        raw_json = json.loads(strip_markdown_json_fence(text))
        return response_schema.model_validate(raw_json)
    except (JSONDecodeError, ValidationError, TypeError) as exc:
        raise LLMStructuredOutputError("AI provider returned malformed structured output") from exc


def extract_output_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text

    output = getattr(response, "output", None)
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if isinstance(content, list):
                for content_item in content:
                    text = getattr(content_item, "text", None)
                    if isinstance(text, str):
                        chunks.append(text)
        if chunks:
            return "".join(chunks)

    raise LLMStructuredOutputError("AI provider response did not include parseable text output")
