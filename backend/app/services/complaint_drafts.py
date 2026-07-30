from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import PharmaQSentinelError
from app.models import ActorType, ComplaintDraft, ComplaintStatus
from app.models.base import new_uuid, utc_now
from app.repositories.audit_events import AuditEventRepository
from app.repositories.complaint_drafts import ComplaintDraftRepository
from app.schemas.complaints import (
    ComplaintDraftDevelopmentPatchRequest,
    ComplaintDraftStatusResponse,
)

MUTABLE_COMPLAINT_FIELDS = (
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
)

LOCKED_STATUSES = {
    ComplaintStatus.COMMITTED.value,
    ComplaintStatus.CLOSED.value,
    ComplaintStatus.CANCELLED.value,
}


class ComplaintDraftLockedError(PharmaQSentinelError):
    def __init__(self, draft_id: str) -> None:
        super().__init__(f"Complaint draft is locked and cannot be changed: {draft_id}", status_code=409)


class DevelopmentPatchDisabledError(PharmaQSentinelError):
    def __init__(self) -> None:
        super().__init__("Development patch endpoint is not enabled", status_code=404)


def _serialise_audit_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _field_snapshot(draft: ComplaintDraft) -> dict[str, object]:
    return {
        field_name: _serialise_audit_value(getattr(draft, field_name))
        for field_name in MUTABLE_COMPLAINT_FIELDS
    }


def _normalise_patch_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value


def _is_locked(draft: ComplaintDraft) -> bool:
    return draft.status in LOCKED_STATUSES


def _validate_mutable(draft: ComplaintDraft) -> None:
    if _is_locked(draft):
        raise ComplaintDraftLockedError(draft.id)


def _generate_thread_id() -> str:
    return f"thread-{new_uuid()}"


def create_empty_draft(db: Any, *, created_by: str | None) -> ComplaintDraft:
    draft = ComplaintDraftRepository(db).create(
        thread_id=_generate_thread_id(),
        created_by=created_by,
        status=ComplaintStatus.DRAFT.value,
    )
    AuditEventRepository(db).append(
        draft_id=draft.id,
        event_type="DRAFT_CREATED",
        actor_type=ActorType.USER if created_by else ActorType.SYSTEM,
        actor_identifier=created_by,
        tool_name="complaint_draft_lifecycle",
        reason="Created empty complaint draft",
        old_value=None,
        new_value={
            "id": draft.id,
            "thread_id": draft.thread_id,
            "status": draft.status,
        },
        metadata_json={"source": "complaint_draft_api"},
    )
    return draft


def restore_draft(db: Any, *, draft_id: str, actor_identifier: str | None = None) -> ComplaintDraft:
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    AuditEventRepository(db).append(
        draft_id=draft.id,
        event_type="DRAFT_RESTORED",
        actor_type=ActorType.SYSTEM,
        actor_identifier=actor_identifier,
        tool_name="complaint_draft_lifecycle",
        reason="Restored active draft from persisted identifier",
        old_value=None,
        new_value={
            "id": draft.id,
            "thread_id": draft.thread_id,
            "status": draft.status,
        },
        metadata_json={"source": "session_restore"},
    )
    return draft


def get_draft_status(db: Any, *, draft_id: str) -> ComplaintDraftStatusResponse:
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    return ComplaintDraftStatusResponse(
        id=draft.id,
        status=draft.status,
        updated_at=draft.updated_at,
        is_locked=_is_locked(draft),
        is_committed=draft.status == ComplaintStatus.COMMITTED.value,
        is_extraction_active=False,
    )


def reset_draft(db: Any, *, draft_id: str, actor_identifier: str | None = None) -> ComplaintDraft:
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    _validate_mutable(draft)

    old_values = _field_snapshot(draft)
    for field_name in MUTABLE_COMPLAINT_FIELDS:
        setattr(draft, field_name, None)
    draft.status = ComplaintStatus.DRAFT.value
    draft.updated_at = utc_now()

    AuditEventRepository(db).append(
        draft_id=draft.id,
        event_type="DRAFT_RESET",
        actor_type=ActorType.USER if actor_identifier else ActorType.SYSTEM,
        actor_identifier=actor_identifier,
        tool_name="complaint_draft_lifecycle",
        reason="Reset mutable complaint draft fields",
        old_value=old_values,
        new_value=_field_snapshot(draft),
        metadata_json={"source": "reset_form"},
    )
    db.flush()
    return draft


def apply_development_patch(
    db: Any,
    *,
    draft_id: str,
    request: ComplaintDraftDevelopmentPatchRequest,
) -> ComplaintDraft:
    settings = get_settings()
    if settings.app_env != "development" or not settings.enable_development_patch_endpoint:
        raise DevelopmentPatchDisabledError()

    draft = ComplaintDraftRepository(db).get_required(draft_id)
    _validate_mutable(draft)

    patch_values = {
        field_name: _normalise_patch_value(value)
        for field_name, value in request.patch.model_dump(exclude_unset=True).items()
    }
    manufacturing_date = patch_values.get("manufacturing_date", draft.manufacturing_date)
    expiry_retest_date = patch_values.get("expiry_retest_date", draft.expiry_retest_date)
    if manufacturing_date is not None and expiry_retest_date is not None:
        if expiry_retest_date < manufacturing_date:
            raise PharmaQSentinelError(
                "expiry_retest_date cannot be before manufacturing_date",
                status_code=422,
            )

    audit_repository = AuditEventRepository(db)
    changed_fields: list[str] = []
    for field_name, new_value in patch_values.items():
        old_value = getattr(draft, field_name)
        if old_value == new_value:
            continue

        setattr(draft, field_name, new_value)
        changed_fields.append(field_name)
        audit_repository.append(
            draft_id=draft.id,
            event_type="DEVELOPMENT_PATCH_APPLIED",
            actor_type=ActorType.USER,
            actor_identifier=request.actor_identifier,
            tool_name="development_patch_endpoint",
            field_name=field_name,
            old_value={"value": _serialise_audit_value(old_value)},
            new_value={"value": _serialise_audit_value(new_value)},
            reason=request.reason,
            metadata_json={
                "source": request.source,
                "changed_fields": changed_fields,
            },
        )

    if changed_fields:
        draft.updated_at = utc_now()
    db.flush()
    return draft
