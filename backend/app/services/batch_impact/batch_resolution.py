from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Batch, ComplaintDraft
from app.repositories.reference import BatchRepository

_BATCH_SUFFIX_PATTERN = re.compile(r"(\d{6,})$")


@dataclass(frozen=True)
class BatchResolution:
    batch: Batch
    requested_batch_number: str
    exact_match: bool
    limitation: str | None = None


def _normalise_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _product_names_overlap(draft_product_name: str | None, batch: Batch) -> bool:
    draft_name = _normalise_text(draft_product_name)
    product_name = _normalise_text(batch.product.product_name if batch.product else None)
    if not draft_name or not product_name:
        return False
    return draft_name in product_name or product_name in draft_name


def resolve_reference_batch(db: Session, draft: ComplaintDraft) -> BatchResolution | None:
    if not draft.batch_lot_number:
        return None

    requested = draft.batch_lot_number.strip().upper()
    repository = BatchRepository(db)
    exact = repository.get_by_batch_number(requested)
    if exact is not None:
        return BatchResolution(batch=exact, requested_batch_number=requested, exact_match=True)

    suffix_match = _BATCH_SUFFIX_PATTERN.search(requested)
    if suffix_match is None:
        return None

    suffix_candidates = repository.list_by_batch_suffix(suffix_match.group(1))
    product_candidates = [
        candidate for candidate in suffix_candidates if _product_names_overlap(draft.product_name, candidate)
    ]
    if len(product_candidates) == 1:
        candidate = product_candidates[0]
        match_basis = "single same-product suffix match"
    elif not draft.product_name and len(suffix_candidates) == 1:
        candidate = suffix_candidates[0]
        match_basis = "single suffix match because product was not provided"
    else:
        return None

    return BatchResolution(
        batch=candidate,
        requested_batch_number=requested,
        exact_match=False,
        limitation=(
            f"The draft reported batch {requested}, but the seeded demonstration reference "
            f"records contain {candidate.batch_number}. Batch Intelligence used a {match_basis} "
            "as demo context; a qualified reviewer must verify the true batch record before action."
        ),
    )
