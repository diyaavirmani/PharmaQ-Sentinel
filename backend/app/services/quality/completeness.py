from __future__ import annotations

from app.services.quality.follow_up_questions import questions_for_missing_fields
from app.services.quality.schemas import CompletenessResult

COMPLETENESS_VERSION = "complaint-completeness-v1"

CRITICAL_FIELDS = (
    ("detailed_description", "complaint description"),
    ("product_name", "product identification"),
    ("complaint_source", "complaint source"),
    ("customer_name", "customer identification"),
    ("batch_lot_number", "batch or lot"),
    ("complaint_date", "receipt date"),
)
CONDITIONAL_NON_BLOCKING = {"batch or lot", "receipt date", "customer identification"}
RECOMMENDED_FIELDS = (
    ("product_strength_grade", "strength or grade"),
    ("dosage_form", "dosage form"),
    ("quantity_affected", "quantity affected"),
    ("defect_observed_date", "defect-observed date"),
    ("sample_available", "sample availability"),
    ("photograph_available", "photograph availability"),
    ("patient_consumed_product", "patient consumption status"),
    ("adverse_event_signal", "adverse-event information"),
    ("storage_conditions", "storage conditions"),
    ("customer_contact", "reporter contact"),
    ("country_market", "market or country"),
    ("return_sample_arrangement", "return sample arrangement"),
)


def _has_value(complaint: dict[str, object | None], field_name: str) -> bool:
    if field_name not in complaint:
        return False
    return complaint[field_name] not in (None, "", [], {})


def evaluate_completeness(complaint: dict[str, object | None]) -> CompletenessResult:
    missing_critical = [
        label
        for field_name, label in CRITICAL_FIELDS
        if not _has_value(complaint, field_name)
    ]
    missing_recommended = [
        label
        for field_name, label in RECOMMENDED_FIELDS
        if not _has_value(complaint, field_name)
    ]
    blocking_missing = [field for field in missing_critical if field not in CONDITIONAL_NON_BLOCKING]
    total = len(CRITICAL_FIELDS) + len(RECOMMENDED_FIELDS)
    missing_count = len(missing_critical) + len(missing_recommended)
    completeness_percentage = round(((total - missing_count) / total) * 100)
    blockers = [
        f"{field.title()} is needed before meaningful triage can begin."
        for field in blocking_missing
    ]
    warnings = []
    if "batch or lot" in missing_critical:
        warnings.append("Batch or lot is missing; this should be requested when available but does not automatically block triage.")
    if "adverse-event information" in missing_recommended and complaint.get("adverse_event_signal") is True:
        warnings.append("A possible adverse-event signal exists but supporting event details are incomplete.")

    priority_missing = [*blocking_missing, *missing_recommended, *missing_critical]
    return CompletenessResult(
        completeness_percentage=max(0, min(100, completeness_percentage)),
        can_begin_triage=not blocking_missing,
        missing_critical_fields=missing_critical,
        missing_recommended_fields=missing_recommended,
        targeted_follow_up_questions=questions_for_missing_fields(priority_missing, limit=3),
        blockers=blockers,
        warnings=warnings,
    )


def missing_field_labels(complaint: dict[str, object | None]) -> list[str]:
    result = evaluate_completeness(complaint)
    return [*result.missing_critical_fields, *result.missing_recommended_fields]
