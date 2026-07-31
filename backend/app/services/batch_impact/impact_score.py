from __future__ import annotations

from app.services.batch_impact.schemas import BatchImpactSignal

PRIORITY_ORDER = {"INFO": 0, "WATCH": 1, "ELEVATED": 2, "HIGH": 3}


def overall_priority(signals: list[BatchImpactSignal]) -> str:
    if not signals:
        return "NORMAL"
    highest = max(PRIORITY_ORDER[signal.level] for signal in signals)
    if highest >= PRIORITY_ORDER["HIGH"]:
        return "HIGH"
    if highest >= PRIORITY_ORDER["ELEVATED"]:
        return "ELEVATED"
    if highest >= PRIORITY_ORDER["WATCH"]:
        return "WATCH"
    return "NORMAL"
