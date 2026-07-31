from __future__ import annotations

from app.models import ComplaintDraft, HistoricalComplaint
from app.services.complaint_intelligence.schemas import RecurrenceSignal


def recurrence_signals_for(
    *,
    draft: ComplaintDraft,
    candidates: list[HistoricalComplaint],
) -> list[RecurrenceSignal]:
    signals: list[RecurrenceSignal] = []
    same_product_type = [
        candidate
        for candidate in candidates
        if candidate.product and candidate.product.product_name == draft.product_name
        and candidate.complaint_type == draft.complaint_type
    ]
    if len(same_product_type) >= 2:
        signals.append(
            RecurrenceSignal(
                signal_type="SAME_PRODUCT_DEFECT_TREND",
                description=f"{len(same_product_type)} historical records share the same product and complaint type.",
                evidence_references=[candidate.id for candidate in same_product_type[:5]],
                limitation="Small seeded demo dataset; this is a recurrence signal, not a statistical trend confirmation.",
            )
        )
    shared_packaging = [
        candidate
        for candidate in candidates
        if candidate.batch
        and any(lot for lot in candidate.batch.packaging_material_lots)
        and draft.batch_lot_number
    ]
    if len(shared_packaging) >= 2:
        signals.append(
            RecurrenceSignal(
                signal_type="SHARED_PACKAGING_OR_BATCH_CONTEXT",
                description="Related complaints have batch records with packaging-lot context available for review.",
                evidence_references=[candidate.id for candidate in shared_packaging[:5]],
                limitation="Packaging association requires batch-record confirmation before investigation conclusions.",
            )
        )
    after_capa = [
        candidate
        for candidate in candidates
        if candidate.batch and any(deviation.capas for deviation in candidate.batch.deviations)
    ]
    if after_capa:
        signals.append(
            RecurrenceSignal(
                signal_type="COMPLAINTS_WITH_CAPA_CONTEXT",
                description="One or more historical complaints have linked deviation/CAPA context available for QA review.",
                evidence_references=[candidate.id for candidate in after_capa[:5]],
                limitation="CAPA context is a review prompt only and does not imply CAPA ineffectiveness.",
            )
        )
    return signals
