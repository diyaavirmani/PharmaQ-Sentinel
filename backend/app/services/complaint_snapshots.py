from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.models import ComplaintDraft, ComplaintVersion
from app.models.base import utc_now
from app.repositories.complaint_drafts import ComplaintDraftRepository
from app.repositories.complaint_versions import ComplaintVersionRepository
from app.repositories.complaints import ComplaintRepository

SNAPSHOT_FIELDS = (
    "id",
    "thread_id",
    "status",
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
    "expiry_retest_date",
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
    "created_by",
    "created_at",
    "updated_at",
)


def _serialise_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        utc_value = value.replace(tzinfo=UTC)
    else:
        utc_value = value.astimezone(UTC)
    return utc_value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _serialise_decimal(field_name: str, value: Decimal) -> str:
    if field_name == "risk_confidence":
        return str(value.quantize(Decimal("0.0001")))
    if field_name == "quantity_affected":
        return str(value.quantize(Decimal("0.001")))
    return format(value, "f")


def canonicalise_value(value: Any, *, field_name: str = "") -> Any:
    if isinstance(value, datetime):
        return _serialise_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return _serialise_decimal(field_name, value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): canonicalise_value(item, field_name=str(key)) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [canonicalise_value(item, field_name=field_name) for item in value]
    return value


def draft_to_canonical_dict(draft: ComplaintDraft) -> dict[str, Any]:
    snapshot = {
        field_name: canonicalise_value(getattr(draft, field_name), field_name=field_name)
        for field_name in SNAPSHOT_FIELDS
    }
    return dict(sorted(snapshot.items()))


def serialise_snapshot(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def checksum_snapshot(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(serialise_snapshot(snapshot).encode("utf-8")).hexdigest()


class ComplaintSnapshotService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.drafts = ComplaintDraftRepository(db)
        self.complaints = ComplaintRepository(db)
        self.versions = ComplaintVersionRepository(db)

    def create_version_from_draft(
        self,
        *,
        draft_id: str,
        complaint_id: str,
        created_by: str,
        change_reason: str | None = None,
        version_number: int | None = None,
    ) -> ComplaintVersion:
        draft = self.drafts.get_required(draft_id)
        self.complaints.get_required(complaint_id)
        snapshot = draft_to_canonical_dict(draft)
        checksum = checksum_snapshot(snapshot)
        latest = self.versions.get_latest_for_complaint(complaint_id)
        next_version_number = version_number or ((latest.version_number + 1) if latest else 1)
        return self.versions.append(
            complaint_id=complaint_id,
            version_number=next_version_number,
            snapshot=snapshot,
            checksum=checksum,
            created_by=created_by,
            created_at=utc_now(),
            change_reason=change_reason,
        )
