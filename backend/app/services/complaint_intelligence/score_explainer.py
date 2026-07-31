from __future__ import annotations


def recommended_action(classification: str) -> str:
    actions = {
        "LIKELY_EXACT_DUPLICATE": "Open manual duplicate review before creating a separate official record.",
        "POSSIBLE_DUPLICATE": "Compare source evidence and decide whether the candidate is a duplicate or related record.",
        "RECURRENCE_SIGNAL": "Assess recurrence trend and whether investigation scope should include related records.",
        "RELATED_QUALITY_SIGNAL": "Use as supporting context only; do not merge without QA review.",
    }
    return actions.get(classification, "No duplicate action recommended.")


def classify(total_score: int, *, recurrence: bool) -> str:
    if total_score >= 80:
        return "LIKELY_EXACT_DUPLICATE"
    if total_score >= 55:
        return "POSSIBLE_DUPLICATE"
    if recurrence or total_score >= 35:
        return "RECURRENCE_SIGNAL"
    if total_score >= 20:
        return "RELATED_QUALITY_SIGNAL"
    return "UNRELATED"
