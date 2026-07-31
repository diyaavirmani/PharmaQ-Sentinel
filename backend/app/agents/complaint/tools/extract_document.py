from __future__ import annotations

import json
from typing import Any

from app.agents.complaint.constants import PROMPT_VERSION_DOCUMENT_EXTRACTION
from app.agents.complaint.prompts import DOCUMENT_EXTRACTION_PROMPT
from app.agents.complaint.schemas import (
    DocumentComplaintExtraction,
    DocumentFieldEvidence,
)
from app.agents.complaint.state import ComplaintAssistantState
from app.agents.complaint.tools.log_complaint import SUPPORTED_LOG_FIELDS, _deterministic_extraction
from app.models import ExtractionStatus
from app.repositories import ComplaintAttachmentRepository
from app.services.llm import LLMGatewayError, LLMRequestContext, StructuredLLMResult


def _structured_document_extraction(
    runtime: Any,
    state: ComplaintAssistantState,
    attachment: object,
) -> tuple[DocumentComplaintExtraction, StructuredLLMResult[DocumentComplaintExtraction]]:
    metadata = attachment.extraction_metadata or {}
    payload = {
        "attachment_id": attachment.id,
        "document_type": metadata.get("document_type"),
        "detected_mime_type": attachment.mime_type,
        "text": attachment.extracted_text,
        "segments": metadata.get("segments", []),
    }
    result = runtime.llm_gateway.generate_structured(
        system_instructions=DOCUMENT_EXTRACTION_PROMPT,
        user_input=json.dumps(payload, sort_keys=True, default=str),
        response_schema=DocumentComplaintExtraction,
        request_context=LLMRequestContext(
            request_id=state["request_id"],
            draft_id=state["draft_id"],
            thread_id=state["thread_id"],
            tool_name="EXTRACT_DOCUMENT",
            purpose="Extract complaint draft fields from uploaded document text",
            prompt_version=PROMPT_VERSION_DOCUMENT_EXTRACTION,
            contains_sensitive_information=True,
            metadata={"attachment_id": attachment.id, "text_length": len(attachment.extracted_text or "")},
        ),
        temperature=0,
        max_output_tokens=2200,
    )
    return result.parsed_output, result


def _fallback_document_extraction(attachment: object) -> DocumentComplaintExtraction:
    fallback = _deterministic_extraction(attachment.extracted_text or "")
    metadata = attachment.extraction_metadata or {}
    segments = metadata.get("segments") if isinstance(metadata, dict) else []
    first_segment = segments[0] if isinstance(segments, list) and segments else {}
    evidence = []
    for field_name, extracted in fallback.extracted_fields.items():
        evidence.append(
            DocumentFieldEvidence(
                field_name=field_name,
                value=extracted.normalised if extracted.normalised is not None else extracted.value,
                attachment_id=attachment.id,
                page_number=first_segment.get("page_number") if isinstance(first_segment, dict) else None,
                paragraph_index=(
                    first_segment.get("paragraph_index") if isinstance(first_segment, dict) else None
                ),
                source_excerpt=extracted.source_excerpt or (attachment.extracted_text or "")[:500],
                confidence=extracted.confidence or 0.55,
                explicitly_stated=extracted.explicitly_stated,
                normalised=extracted.normalised,
                extraction_method="DOCUMENT_EXTRACTION",
            )
        )
    return DocumentComplaintExtraction(
        document_type=str(metadata.get("document_type") or "UNKNOWN"),
        detected_language=fallback.detected_language,
        extracted_fields=fallback.extracted_fields,
        evidence_by_field=evidence,
        complaint_classification=fallback.complaint_classification,
        possible_safety_signals=[],
        missing_fields=fallback.missing_fields,
        extraction_confidence=0.55,
        warnings=[*fallback.warnings, "Used deterministic fallback document structuring."],
        concise_summary=fallback.concise_summary,
    )


def build_extract_document_state(runtime: Any, state: ComplaintAssistantState) -> ComplaintAssistantState:
    warnings = list(state["warnings"])
    if not state["attachment_id"]:
        return {
            **state,
            "tool_name": "EXTRACT_DOCUMENT",
            "tool_implemented": True,
            "assistant_response": "Please upload a supported complaint document before extraction.",
            "clarification_required": True,
        }

    attachment_repository = ComplaintAttachmentRepository(runtime.db)
    attachment = attachment_repository.get_for_draft(state["draft_id"], state["attachment_id"])
    if attachment is None:
        return {
            **state,
            "tool_name": "EXTRACT_DOCUMENT",
            "tool_implemented": True,
            "assistant_response": "The uploaded document could not be found for this draft.",
            "clarification_required": True,
        }
    attachment_repository.update_extraction_state(
        attachment,
        status=ExtractionStatus.EXTRACTING,
        stage="STRUCTURING_FIELDS",
        progress=70,
    )

    provider = state["provider"]
    requested_model = state["requested_model"]
    actual_model = state["actual_model"]
    prompt_versions = dict(state["prompt_versions"])
    try:
        extraction, llm_result = _structured_document_extraction(runtime, state, attachment)
        provider = llm_result.provider
        requested_model = llm_result.requested_model
        actual_model = llm_result.actual_model
        prompt_versions["document_extraction"] = llm_result.prompt_version
        warnings.extend(llm_result.warnings)
    except LLMGatewayError as exc:
        extraction = _fallback_document_extraction(attachment)
        warnings.append(f"OpenAI document extraction unavailable; used safe deterministic extraction ({exc.__class__.__name__}).")

    patch: dict[str, object] = {}
    field_metadata: dict[str, dict[str, object]] = {}
    evidence_by_field = {item.field_name: item for item in extraction.evidence_by_field}
    for field_name, extracted in extraction.extracted_fields.items():
        if field_name not in SUPPORTED_LOG_FIELDS:
            warnings.append(f"Ignored unsupported document field: {field_name}.")
            continue
        value = extracted.normalised if extracted.normalised is not None else extracted.value
        if value is None:
            continue
        patch[field_name] = value
        evidence = evidence_by_field.get(field_name)
        metadata = extracted.model_dump(mode="json")
        if evidence:
            metadata.update(evidence.model_dump(mode="json"))
        metadata["attachment_id"] = attachment.id
        metadata["mime_type"] = attachment.mime_type
        field_metadata[field_name] = metadata

    patch["missing_fields"] = {field: "Not provided" for field in extraction.missing_fields}
    attachment_repository.update_extraction_state(
        attachment,
        stage="VALIDATING_FIELDS",
        progress=82,
    )
    return {
        **state,
        "tool_name": "EXTRACT_DOCUMENT",
        "tool_implemented": True,
        "proposed_patch": patch if patch else None,
        "accepted_field_metadata": field_metadata,
        "extraction_result": extraction.model_dump(mode="json"),
        "provider": provider,
        "requested_model": requested_model,
        "actual_model": actual_model,
        "prompt_versions": prompt_versions,
        "warnings": [*warnings, *extraction.warnings],
    }
