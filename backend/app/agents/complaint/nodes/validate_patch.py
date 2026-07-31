from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.agents.complaint.constants import ComplaintAssistantIntent
from app.agents.complaint.state import ComplaintAssistantState
from app.models.enums import Priority, ProductType, SafetyRoute, Severity

ALLOWED_PATCH_FIELDS = {
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
    "suggested_severity",
    "suggested_priority",
    "safety_route",
    "risk_rationale",
    "potential_hazard",
    "suggested_next_action",
    "risk_confidence",
    "missing_fields",
}
BOOLEAN_FIELDS = {
    "sample_available",
    "patient_consumed_product",
    "adverse_event_signal",
    "counterfeit_signal",
}
DATE_FIELDS = {"manufacturing_date", "expiry_retest_date", "complaint_date", "defect_observed_date"}
TEXT_FIELDS = ALLOWED_PATCH_FIELDS - BOOLEAN_FIELDS - DATE_FIELDS - {"quantity_affected", "risk_confidence", "missing_fields"}
BATCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{1,149}$")
MONTH_YEAR_PATTERN = re.compile(
    r"^(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}$",
    re.IGNORECASE,
)


def _clean_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    stripped = " ".join(value.strip().split())
    return stripped or None


def _parse_decimal(value: object, *, field_name: str, errors: list[str]) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        errors.append(f"{field_name} must be numeric.")
        return None
    if parsed < 0:
        errors.append(f"{field_name} cannot be negative.")
        return None
    return parsed


def _parse_confidence(value: object, errors: list[str]) -> Decimal | None:
    parsed = _parse_decimal(value, field_name="risk_confidence", errors=errors)
    if parsed is not None and parsed > 1:
        errors.append("risk_confidence must be between 0 and 1.")
        return None
    return parsed


def _parse_exact_date(value: object, *, field_name: str, patch: dict[str, object], warnings: list[str]) -> date | None:
    if isinstance(value, date):
        return value
    cleaned = _clean_string(value)
    if cleaned is None:
        return None
    if MONTH_YEAR_PATTERN.match(cleaned) and field_name in {"manufacturing_date", "expiry_retest_date"}:
        patch[f"{field_name}_text"] = cleaned
        warnings.append(f"{field_name} was provided as month/year only and stored as text.")
        return None
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        warnings.append(f"Ignored invalid or partial {field_name}; exact calendar date was not provided.")
        return None


def _validate_enum(value: object, enum_type: type, *, field_name: str, errors: list[str]) -> str | None:
    cleaned = _clean_string(value)
    if cleaned is None:
        return None
    upper = cleaned.upper()
    valid_values = {item.value for item in enum_type}
    if upper not in valid_values:
        errors.append(f"{field_name} has unsupported value {cleaned}.")
        return None
    return upper


def validate_patch_node(state: ComplaintAssistantState) -> ComplaintAssistantState:
    if state["proposed_patch"] is None:
        return {**state, "validated_patch": None, "changed_fields": []}

    warnings = list(state["warnings"])
    errors = list(state["errors"])
    validated: dict[str, object] = {}

    for field_name, raw_value in state["proposed_patch"].items():
        if field_name not in ALLOWED_PATCH_FIELDS:
            warnings.append(f"Ignored unsupported patch field: {field_name}.")
            continue
        operation = state.get("accepted_field_metadata", {}).get(field_name, {}).get("operation")
        is_explicit_clear = (
            state["intent"] == ComplaintAssistantIntent.EDIT_COMPLAINT.value
            and operation == "CLEAR"
        )
        if raw_value is None and not is_explicit_clear:
            continue
        if is_explicit_clear:
            validated[field_name] = None
            continue

        if field_name in TEXT_FIELDS:
            value = _clean_string(raw_value)
            if value is None:
                continue
            if field_name == "batch_lot_number" and not BATCH_PATTERN.match(value):
                errors.append("batch_lot_number contains unsupported characters.")
                continue
            if field_name == "quantity_unit" and any(char.isdigit() for char in value):
                errors.append("quantity_unit must not contain a quantity value.")
                continue
            if field_name == "product_type":
                value = _validate_enum(value, ProductType, field_name=field_name, errors=errors)
            elif field_name == "suggested_severity":
                value = _validate_enum(value, Severity, field_name=field_name, errors=errors)
            elif field_name == "suggested_priority":
                value = _validate_enum(value, Priority, field_name=field_name, errors=errors)
            elif field_name == "safety_route":
                value = _validate_enum(value, SafetyRoute, field_name=field_name, errors=errors)
            if value is not None:
                validated[field_name] = value
            continue

        if field_name in DATE_FIELDS:
            parsed_date = _parse_exact_date(raw_value, field_name=field_name, patch=validated, warnings=warnings)
            if parsed_date is not None:
                validated[field_name] = parsed_date
            continue

        if field_name == "quantity_affected":
            quantity = _parse_decimal(raw_value, field_name=field_name, errors=errors)
            if quantity is not None:
                validated[field_name] = quantity
            continue

        if field_name == "risk_confidence":
            confidence = _parse_confidence(raw_value, errors)
            if confidence is not None:
                validated[field_name] = confidence
            continue

        if field_name in BOOLEAN_FIELDS:
            if isinstance(raw_value, bool):
                validated[field_name] = raw_value
            else:
                warnings.append(f"Ignored non-boolean {field_name}.")
            continue

        if field_name == "missing_fields" and isinstance(raw_value, dict):
            validated[field_name] = raw_value

    manufacture = validated.get("manufacturing_date") or state["existing_complaint"].get("manufacturing_date")
    expiry = validated.get("expiry_retest_date") or state["existing_complaint"].get("expiry_retest_date")
    if manufacture and expiry and str(expiry) < str(manufacture):
        warnings.append("Expiry/retest date appears earlier than manufacturing date; QA review required.")

    if errors:
        return {
            **state,
            "validated_patch": None,
            "changed_fields": [],
            "warnings": warnings,
            "errors": errors,
            "assistant_response": "I could not apply that correction because one or more values failed validation.",
        }

    return {
        **state,
        "validated_patch": validated if validated else None,
        "changed_fields": [],
        "warnings": warnings,
        "errors": errors,
    }
