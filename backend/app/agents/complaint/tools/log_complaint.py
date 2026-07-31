from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.agents.complaint.constants import PROMPT_VERSION_LOG_COMPLAINT
from app.agents.complaint.prompts import LOG_COMPLAINT_EXTRACTION_PROMPT
from app.agents.complaint.schemas import ComplaintExtractionResult, ComplaintFieldExtraction
from app.agents.complaint.state import ComplaintAssistantState
from app.services.llm import LLMGatewayError, LLMRequestContext, StructuredLLMResult

SUPPORTED_LOG_FIELDS = {
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

MONTH_YEAR_PATTERN = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}\b",
    re.IGNORECASE,
)
BATCH_PATTERN = re.compile(r"\bbatch\s+([A-Z0-9][A-Z0-9._/-]{2,149})\b", re.IGNORECASE)
QUANTITY_PATTERN = re.compile(r"\b(\d+(?:\.\d{1,3})?)\s+([A-Za-z][A-Za-z -]{1,48})\b")
STRENGTH_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|kg|ml|iu|%)\b", re.IGNORECASE)
CUSTOMER_PATTERN = re.compile(r"^\s*([A-Z][A-Za-z0-9 &.'-]{2,120}?)\s+(?:reported|reports|complained|raised)\b")


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = " ".join(value.strip().split())
    return stripped or None


def _field(value: object, *, excerpt: str, confidence: float = 0.72) -> ComplaintFieldExtraction:
    return ComplaintFieldExtraction(
        value=value,
        original_text=str(value) if value is not None else None,
        explicitly_stated=True,
        normalised=value,
        confidence=confidence,
        source_excerpt=excerpt[:1000],
    )


def _add_if_present(
    fields: dict[str, ComplaintFieldExtraction],
    field_name: str,
    value: object | None,
    *,
    excerpt: str,
    confidence: float = 0.72,
) -> None:
    if value is not None:
        fields[field_name] = _field(value, excerpt=excerpt, confidence=confidence)


def _deterministic_extraction(message: str) -> ComplaintExtractionResult:
    lowered = message.lower()
    fields: dict[str, ComplaintFieldExtraction] = {}

    customer_match = CUSTOMER_PATTERN.search(message)
    if customer_match:
        customer = customer_match.group(1).strip()
        _add_if_present(fields, "customer_name", customer, excerpt=customer_match.group(0), confidence=0.74)
        if "pharmacy" in customer.lower():
            _add_if_present(fields, "complaint_source", "Pharmacy", excerpt=customer_match.group(0), confidence=0.7)

    batch_match = BATCH_PATTERN.search(message)
    if batch_match:
        _add_if_present(fields, "batch_lot_number", batch_match.group(1), excerpt=batch_match.group(0), confidence=0.86)

    quantity_match = QUANTITY_PATTERN.search(message)
    if quantity_match:
        try:
            quantity = Decimal(quantity_match.group(1))
            unit = quantity_match.group(2).strip().lower()
            _add_if_present(fields, "quantity_affected", str(quantity), excerpt=quantity_match.group(0), confidence=0.78)
            _add_if_present(fields, "quantity_unit", unit, excerpt=quantity_match.group(0), confidence=0.76)
        except InvalidOperation:
            pass

    strength_match = STRENGTH_PATTERN.search(message)
    if strength_match:
        strength = f"{strength_match.group(1)} {strength_match.group(2).lower()}"
        _add_if_present(fields, "product_strength_grade", strength, excerpt=strength_match.group(0), confidence=0.82)

    product_match = re.search(
        r"\b(?:discolou?red|broken|missing|leaking|leakage|wrong|foreign|assay|moisture|damaged)\s+"
        r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})",
        message,
    )
    if product_match:
        product_name = product_match.group(1).strip()
        product_name = STRENGTH_PATTERN.sub("", product_name).strip()
        _add_if_present(fields, "product_name", product_name, excerpt=product_match.group(0), confidence=0.62)
    elif "amoxicillin capsules" in lowered:
        _add_if_present(fields, "product_name", "Amoxicillin Capsules", excerpt="Amoxicillin Capsules", confidence=0.78)

    if "api" in lowered:
        _add_if_present(fields, "product_type", "API", excerpt="API", confidence=0.78)
    elif any(term in lowered for term in ("capsule", "tablet", "injection", "blister")):
        _add_if_present(fields, "product_type", "FDF", excerpt=message[:200], confidence=0.68)

    if any(term in lowered for term in ("discoloured", "discolored", "colour variation", "color variation")):
        _add_if_present(fields, "complaint_type", "Product appearance", excerpt=message[:300], confidence=0.82)
        _add_if_present(fields, "detailed_description", "Discoloured capsules", excerpt=message[:300], confidence=0.78)
    elif "assay" in lowered:
        _add_if_present(fields, "complaint_type", "API assay discrepancy", excerpt=message[:300], confidence=0.78)
    elif "moisture" in lowered:
        _add_if_present(fields, "complaint_type", "API moisture discrepancy", excerpt=message[:300], confidence=0.78)
    elif "leak" in lowered:
        _add_if_present(fields, "complaint_type", "Blister leakage", excerpt=message[:300], confidence=0.78)
    elif "foreign" in lowered:
        _add_if_present(fields, "complaint_type", "Foreign particles", excerpt=message[:300], confidence=0.78)
    elif "wrong label" in lowered:
        _add_if_present(fields, "complaint_type", "Wrong label", excerpt=message[:300], confidence=0.78)
    elif "wrong strength" in lowered:
        _add_if_present(fields, "complaint_type", "Wrong strength", excerpt=message[:300], confidence=0.78)

    month_years = MONTH_YEAR_PATTERN.findall(message)
    if month_years:
        _add_if_present(fields, "manufacturing_date_text", month_years[0], excerpt=month_years[0], confidence=0.84)
    if len(month_years) > 1:
        _add_if_present(fields, "expiry_retest_date_text", month_years[1], excerpt=month_years[1], confidence=0.84)

    possible_adverse_event = any(term in lowered for term in ("adverse event", "reaction", "hospital", "rash", "vomit"))
    possible_counterfeit = any(term in lowered for term in ("counterfeit", "tamper", "fake", "seal broken"))

    missing = [
        "customer contact",
        "complaint date",
        "defect observed date",
        "sample availability",
        "patient consumption status",
        "storage conditions",
    ]
    if possible_adverse_event:
        missing.append("adverse-event details")

    return ComplaintExtractionResult(
        extracted_fields=fields,
        complaint_classification=None,
        detected_language="mixed" if re.search(r"\b(hai|mein|me|se)\b", lowered) else "en",
        product_type=fields.get("product_type").value if "product_type" in fields else None,
        possible_quality_defect=bool(fields.get("complaint_type")),
        possible_adverse_event=possible_adverse_event,
        possible_counterfeit=possible_counterfeit,
        missing_fields=missing,
        warnings=["Used deterministic fallback extraction; verify all values carefully."],
        concise_summary=message[:800],
    )


def _structured_extraction(
    runtime: Any,
    state: ComplaintAssistantState,
) -> tuple[ComplaintExtractionResult, StructuredLLMResult[ComplaintExtractionResult]]:
    result = runtime.llm_gateway.generate_structured(
        system_instructions=LOG_COMPLAINT_EXTRACTION_PROMPT,
        user_input=state["latest_user_message"],
        response_schema=ComplaintExtractionResult,
        request_context=LLMRequestContext(
            request_id=state["request_id"],
            draft_id=state["draft_id"],
            thread_id=state["thread_id"],
            tool_name="LOG_COMPLAINT",
            purpose="Extract complaint draft fields from user text",
            prompt_version=PROMPT_VERSION_LOG_COMPLAINT,
            contains_sensitive_information=True,
            metadata={"message_length": len(state["latest_user_message"])},
        ),
        temperature=0,
        max_output_tokens=2200,
    )
    return result.parsed_output, result


def build_log_complaint_state(runtime: Any, state: ComplaintAssistantState) -> ComplaintAssistantState:
    warnings = list(state["warnings"])
    provider = state["provider"]
    requested_model = state["requested_model"]
    actual_model = state["actual_model"]
    prompt_versions = dict(state["prompt_versions"])

    try:
        extraction, llm_result = _structured_extraction(runtime, state)
        provider = llm_result.provider
        requested_model = llm_result.requested_model
        actual_model = llm_result.actual_model
        prompt_versions["log_complaint"] = llm_result.prompt_version
        warnings.extend(llm_result.warnings)
    except LLMGatewayError as exc:
        extraction = _deterministic_extraction(state["latest_user_message"])
        warnings.append(f"OpenAI extraction unavailable; used safe deterministic extraction ({exc.__class__.__name__}).")

    patch: dict[str, object] = {}
    field_metadata: dict[str, dict[str, object]] = {}
    for field_name, extracted in extraction.extracted_fields.items():
        if field_name not in SUPPORTED_LOG_FIELDS:
            warnings.append(f"Ignored unsupported extracted field: {field_name}.")
            continue
        value = extracted.normalised if extracted.normalised is not None else extracted.value
        if value is None:
            continue
        patch[field_name] = value
        field_metadata[field_name] = extracted.model_dump(mode="json")
        if extracted.warning:
            warnings.append(extracted.warning)

    if extraction.product_type and "product_type" not in patch:
        patch["product_type"] = extraction.product_type.value
        field_metadata["product_type"] = {
            "source_excerpt": "Product type classification",
            "confidence": 0.65,
            "explicitly_stated": False,
        }
    patch["adverse_event_signal"] = extraction.possible_adverse_event
    patch["counterfeit_signal"] = extraction.possible_counterfeit
    patch["missing_fields"] = {field: "Not provided" for field in extraction.missing_fields}

    return {
        **state,
        "tool_name": "LOG_COMPLAINT",
        "tool_implemented": True,
        "proposed_patch": patch,
        "accepted_field_metadata": field_metadata,
        "extraction_result": extraction.model_dump(mode="json"),
        "provider": provider,
        "requested_model": requested_model,
        "actual_model": actual_model,
        "prompt_versions": prompt_versions,
        "warnings": [*warnings, *extraction.warnings],
    }
