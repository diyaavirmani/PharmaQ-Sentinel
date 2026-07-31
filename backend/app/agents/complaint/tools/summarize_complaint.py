from __future__ import annotations

SUMMARY_FIELDS = (
    ("complaint_source", "source"),
    ("customer_name", "customer"),
    ("product_name", "product"),
    ("batch_lot_number", "batch or lot"),
    ("complaint_type", "complaint type"),
    ("detailed_description", "description"),
)


def summarize_complaint(existing_complaint: dict[str, object | None]) -> str:
    entered_parts: list[str] = []
    for field_name, label in SUMMARY_FIELDS:
        value = existing_complaint.get(field_name)
        if value is not None:
            entered_parts.append(f"{label}: {value}")

    if not entered_parts:
        return "No complaint details have been entered yet."

    return "Current entered complaint details: " + "; ".join(entered_parts) + "."
