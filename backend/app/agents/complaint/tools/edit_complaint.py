from __future__ import annotations

import json
import re
from typing import Any

from app.agents.complaint.constants import PROMPT_VERSION_EDIT_COMPLAINT
from app.agents.complaint.prompts import EDIT_COMPLAINT_PROMPT
from app.agents.complaint.schemas import ComplaintEditOperation, ComplaintEditResult
from app.agents.complaint.state import ComplaintAssistantState
from app.services.llm import LLMGatewayError, LLMRequestContext, StructuredLLMResult

USER_CORRECTABLE_FIELDS = {
    "complaint_source",
    "customer_name",
    "customer_contact",
    "country_market",
    "product_type",
    "product_name",
    "product_strength_grade",
    "dosage_form",
    "batch_lot_number",
    "manufacturing_date",
    "manufacturing_date_text",
    "expiry_retest_date",
    "expiry_retest_date_text",
    "quantity_affected",
    "quantity_unit",
    "complaint_type",
    "complaint_date",
    "detailed_description",
    "defect_observed_date",
    "sample_available",
    "patient_consumed_product",
    "adverse_event_signal",
    "counterfeit_signal",
    "storage_conditions",
}

BATCH_EDIT_PATTERN = re.compile(r"\bbatch(?:\s+(?:number|lot))?\s+(?:is|to|=)\s+([A-Z0-9][A-Z0-9._/-]{2,149})\b", re.IGNORECASE)
QUANTITY_EDIT_PATTERN = re.compile(r"\b(?:affected\s+)?quantity\s+(?:is|to|=)\s+(-?\d+(?:\.\d{1,3})?)\s*([A-Za-z][A-Za-z -]{1,48})?\b", re.IGNORECASE)
AMBIGUOUS_NUMBER_PATTERN = re.compile(r"\bchange\s+(?:the\s+)?number\s+to\s+(-?\d+(?:\.\d{1,3})?)\b", re.IGNORECASE)
CONTACT_PATTERN = re.compile(r"\b(?:customer\s+)?contact\s+(?:is|to|=)\s+(.+)$", re.IGNORECASE)
COMPLAINT_DATE_PATTERN = re.compile(r"\bcomplaint\s+date\s+(?:is|to|=)\s+([0-9]{4}-[0-9]{2}-[0-9]{2})\b", re.IGNORECASE)
STORAGE_CLEAR_PATTERN = re.compile(r"\b(?:remove|clear|mark\s+as\s+unknown).*\bstorage\b|\bstorage\b.*\b(?:remove|clear|not provided)\b", re.IGNORECASE)


def _operation(
    *,
    field_name: str,
    operation: str,
    new_value: object | None,
    excerpt: str,
    confidence: float = 0.82,
    reason: str = "User explicitly requested a correction.",
) -> ComplaintEditOperation:
    return ComplaintEditOperation(
        field_name=field_name,
        operation=operation,
        new_value=new_value,
        explicitly_requested=True,
        source_excerpt=excerpt[:1000],
        confidence=confidence,
        reason=reason,
    )


def _deterministic_edit(state: ComplaintAssistantState) -> ComplaintEditResult:
    message = state["latest_user_message"]
    lowered = message.lower()
    existing = state["existing_complaint"]
    operations: list[ComplaintEditOperation] = []
    ambiguous: list[str] = []
    warnings: list[str] = []

    ambiguous_match = AMBIGUOUS_NUMBER_PATTERN.search(message)
    if ambiguous_match and existing.get("batch_lot_number") and existing.get("quantity_affected"):
        return ComplaintEditResult(
            operations=[],
            no_op_fields=[],
            ambiguous_requests=[ambiguous_match.group(0)],
            clarification_required=True,
            clarification_question=(
                f"Do you want to change the quantity affected to {ambiguous_match.group(1)}, "
                "or is that number part of another field?"
            ),
            warnings=[],
            concise_summary="Ambiguous numeric correction.",
        )

    batch_match = BATCH_EDIT_PATTERN.search(message)
    if batch_match:
        operations.append(
            _operation(
                field_name="batch_lot_number",
                operation="SET",
                new_value=batch_match.group(1),
                excerpt=batch_match.group(0),
                confidence=0.9,
                reason="User corrected the batch or lot number.",
            )
        )

    quantity_match = QUANTITY_EDIT_PATTERN.search(message)
    if quantity_match:
        operations.append(
            _operation(
                field_name="quantity_affected",
                operation="SET",
                new_value=quantity_match.group(1),
                excerpt=quantity_match.group(0),
                confidence=0.88,
                reason="User corrected the affected quantity.",
            )
        )
        if quantity_match.group(2):
            operations.append(
                _operation(
                    field_name="quantity_unit",
                    operation="SET",
                    new_value=quantity_match.group(2).strip().lower(),
                    excerpt=quantity_match.group(0),
                    confidence=0.84,
                    reason="User provided the affected quantity unit.",
                )
            )

    contact_match = CONTACT_PATTERN.search(message)
    if contact_match:
        operations.append(
            _operation(
                field_name="customer_contact",
                operation="SET",
                new_value=contact_match.group(1).strip(),
                excerpt=contact_match.group(0),
                confidence=0.78,
                reason="User added customer contact information.",
            )
        )

    complaint_date_match = COMPLAINT_DATE_PATTERN.search(message)
    if complaint_date_match:
        operations.append(
            _operation(
                field_name="complaint_date",
                operation="SET",
                new_value=complaint_date_match.group(1),
                excerpt=complaint_date_match.group(0),
                confidence=0.82,
                reason="User corrected the complaint date.",
            )
        )

    if STORAGE_CLEAR_PATTERN.search(message):
        operations.append(
            _operation(
                field_name="storage_conditions",
                operation="CLEAR",
                new_value=None,
                excerpt=message,
                confidence=0.8,
                reason="User explicitly cleared storage conditions.",
            )
        )

    if any(term in lowered for term in ("severity", "priority", "finalise", "finalize")):
        warnings.append("Severity and priority cannot be directly finalised through generic edits.")

    if not operations and not warnings:
        ambiguous.append(message[:300])

    return ComplaintEditResult(
        operations=operations,
        no_op_fields=[],
        ambiguous_requests=ambiguous,
        clarification_required=bool(ambiguous),
        clarification_question="Which complaint field should I update?" if ambiguous else None,
        warnings=warnings,
        concise_summary="Deterministic edit operation parsing.",
    )


def _structured_edit(
    runtime: Any,
    state: ComplaintAssistantState,
) -> tuple[ComplaintEditResult, StructuredLLMResult[ComplaintEditResult]]:
    user_input = json.dumps(
        {
            "current_draft": state["existing_complaint"],
            "user_message": state["latest_user_message"],
        },
        sort_keys=True,
        default=str,
    )
    result = runtime.llm_gateway.generate_structured(
        system_instructions=EDIT_COMPLAINT_PROMPT,
        user_input=user_input,
        response_schema=ComplaintEditResult,
        request_context=LLMRequestContext(
            request_id=state["request_id"],
            draft_id=state["draft_id"],
            thread_id=state["thread_id"],
            tool_name="EDIT_COMPLAINT",
            purpose="Convert user correction into complaint draft edit operations",
            prompt_version=PROMPT_VERSION_EDIT_COMPLAINT,
            contains_sensitive_information=True,
            metadata={"message_length": len(state["latest_user_message"])},
        ),
        temperature=0,
        max_output_tokens=1200,
    )
    return result.parsed_output, result


def build_edit_complaint_state(runtime: Any, state: ComplaintAssistantState) -> ComplaintAssistantState:
    warnings = list(state["warnings"])
    provider = state["provider"]
    requested_model = state["requested_model"]
    actual_model = state["actual_model"]
    prompt_versions = dict(state["prompt_versions"])

    try:
        edit_result, llm_result = _structured_edit(runtime, state)
        provider = llm_result.provider
        requested_model = llm_result.requested_model
        actual_model = llm_result.actual_model
        prompt_versions["edit_complaint"] = llm_result.prompt_version
        warnings.extend(llm_result.warnings)
    except LLMGatewayError as exc:
        edit_result = _deterministic_edit(state)
        warnings.append(f"OpenAI edit parsing unavailable; used safe deterministic parsing ({exc.__class__.__name__}).")

    if edit_result.clarification_required:
        return {
            **state,
            "tool_name": "EDIT_COMPLAINT",
            "tool_implemented": True,
            "proposed_patch": None,
            "validated_patch": None,
            "changed_fields": [],
            "clarification_required": True,
            "clarification_question": edit_result.clarification_question,
            "assistant_response": edit_result.clarification_question or "Please clarify which field should be changed.",
            "provider": provider,
            "requested_model": requested_model,
            "actual_model": actual_model,
            "prompt_versions": prompt_versions,
            "warnings": [*warnings, *edit_result.warnings],
        }

    patch: dict[str, object] = {}
    metadata: dict[str, dict[str, object]] = {}
    for operation in edit_result.operations:
        if operation.field_name not in USER_CORRECTABLE_FIELDS:
            warnings.append(f"Ignored unsupported edit field: {operation.field_name}.")
            continue
        if not operation.explicitly_requested:
            warnings.append(f"Ignored non-explicit edit for field: {operation.field_name}.")
            continue
        patch[operation.field_name] = operation.new_value
        metadata[operation.field_name] = operation.model_dump(mode="json")

    return {
        **state,
        "tool_name": "EDIT_COMPLAINT",
        "tool_implemented": True,
        "proposed_patch": patch if patch else None,
        "accepted_field_metadata": metadata,
        "extraction_result": edit_result.model_dump(mode="json"),
        "provider": provider,
        "requested_model": requested_model,
        "actual_model": actual_model,
        "prompt_versions": prompt_versions,
        "warnings": [*warnings, *edit_result.warnings],
    }
