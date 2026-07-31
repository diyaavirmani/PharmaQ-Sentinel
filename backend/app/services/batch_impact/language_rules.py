from __future__ import annotations

PROHIBITED_CAUSAL_TERMS = (
    " caused ",
    " causes ",
    " causing ",
    " root cause",
    " proves ",
    " proven ",
    " defective",
    " all affected",
    " all impacted",
)


def assert_safe_batch_impact_language(text: str) -> None:
    lowered = f" {text.lower()} "
    for term in PROHIBITED_CAUSAL_TERMS:
        if term in lowered:
            raise ValueError(f"Prohibited causal batch-impact language detected: {term.strip()}")


def safe_connection_limitation() -> str:
    return "Connection is based on seeded records and does not establish causation or final quality impact."


def safe_simulation_limitation() -> str:
    return "Simulation only; it does not place holds, change inventory, notify customers, or perform recall actions."


def validate_payload_language(value: object) -> None:
    if isinstance(value, str):
        assert_safe_batch_impact_language(value)
        return
    if isinstance(value, dict):
        for nested in value.values():
            validate_payload_language(nested)
        return
    if isinstance(value, list):
        for nested in value:
            validate_payload_language(nested)
