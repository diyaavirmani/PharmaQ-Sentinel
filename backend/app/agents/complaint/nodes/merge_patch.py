from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.agents.complaint.constants import ComplaintAssistantIntent
from app.agents.complaint.state import ComplaintAssistantState
from app.core.exceptions import PharmaQSentinelError
from app.models import ActorType, ComplaintStatus, EvidenceType, FieldEvidence, MessageRole
from app.models.base import utc_now
from app.repositories import (
    AuditEventRepository,
    ComplaintDraftRepository,
    ComplaintMessageRepository,
    FieldEvidenceRepository,
)
from app.schemas.complaints import ComplaintDraftResponse


def _serialise_value(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _values_equal(left: object, right: object) -> bool:
    return _serialise_value(left) == _serialise_value(right)


def _ensure_user_message(runtime: Any, state: ComplaintAssistantState) -> dict[str, object]:
    existing = state.get("persisted_user_message")
    if existing:
        return existing
    message = ComplaintMessageRepository(runtime.db).add(
        draft_id=state["draft_id"],
        role=MessageRole.USER,
        message_text=state["latest_user_message"],
        attachment_id=state["attachment_id"],
        metadata_json={
            "request_id": state["request_id"],
            "intent": state["intent"],
            "source": "complaint_assistant",
        },
        created_at=utc_now(),
    )
    return {
        "id": message.id,
        "draft_id": message.draft_id,
        "role": message.role,
        "message_text": message.message_text,
        "attachment_id": message.attachment_id,
        "created_at": message.created_at,
        "metadata_json": message.metadata_json,
    }


def merge_patch_node(runtime: Any):
    def node(state: ComplaintAssistantState) -> ComplaintAssistantState:
        if state["validated_patch"] is None:
            return {**state, "changed_fields": []}

        draft = ComplaintDraftRepository(runtime.db).get_required(state["draft_id"])
        if draft.status in {
            ComplaintStatus.COMMITTED.value,
            ComplaintStatus.CLOSED.value,
            ComplaintStatus.CANCELLED.value,
        }:
            raise PharmaQSentinelError("Complaint draft is locked and cannot be edited.", status_code=409)

        is_edit = state["intent"] == ComplaintAssistantIntent.EDIT_COMPLAINT.value
        is_document = state["intent"] == ComplaintAssistantIntent.EXTRACT_DOCUMENT.value
        user_message = _ensure_user_message(runtime, state)
        user_message_id = str(user_message["id"])
        evidence_repository = FieldEvidenceRepository(runtime.db)
        audit_repository = AuditEventRepository(runtime.db)
        changed_fields: list[str] = []
        conflict_fields: list[str] = []
        no_op_fields: list[str] = []
        warnings = list(state["warnings"])
        field_evidence: list[dict[str, object]] = []
        metadata_by_field = state.get("accepted_field_metadata", {})
        pre_merge_complaint = ComplaintDraftResponse.model_validate(draft).model_dump(mode="json")

        for field_name, new_value in state["validated_patch"].items():
            old_value = getattr(draft, field_name)
            if _values_equal(old_value, new_value):
                no_op_fields.append(field_name)
                continue
            if not is_edit and old_value not in (None, ""):
                conflict_fields.append(field_name)
                warnings.append(f"Kept existing {field_name}; extracted value conflicts with current draft.")
                continue

            setattr(draft, field_name, new_value)
            changed_fields.append(field_name)
            metadata = metadata_by_field.get(field_name, {})
            confidence_value = metadata.get("confidence")
            confidence = Decimal(str(confidence_value)) if confidence_value is not None else None
            if is_edit:
                evidence_type = EvidenceType.USER_CORRECTION
            elif is_document and metadata.get("mime_type") == "application/pdf":
                evidence_type = EvidenceType.PDF
            elif is_document and metadata.get("mime_type") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                evidence_type = EvidenceType.DOCX
            elif is_document and metadata.get("mime_type") == "message/rfc822":
                evidence_type = EvidenceType.EMAIL
            else:
                evidence_type = EvidenceType.USER_TEXT
            if is_edit:
                previous_evidence = runtime.db.scalars(
                    select(FieldEvidence).where(
                        FieldEvidence.draft_id == draft.id,
                        FieldEvidence.field_name == field_name,
                        FieldEvidence.is_active.is_(True),
                    )
                ).all()
                for item in previous_evidence:
                    item.is_active = False
            evidence = evidence_repository.add(
                draft_id=draft.id,
                field_name=field_name,
                field_value={
                    "value": _serialise_value(new_value),
                    "provider": state["provider"],
                    "actual_model": state["actual_model"],
                },
                evidence_type=evidence_type,
                source_attachment_id=str(metadata.get("attachment_id")) if metadata.get("attachment_id") else None,
                source_message_id=user_message_id,
                page_number=metadata.get("page_number") if isinstance(metadata.get("page_number"), int) else None,
                paragraph_index=(
                    metadata.get("paragraph_index")
                    if isinstance(metadata.get("paragraph_index"), int)
                    else None
                ),
                source_excerpt=str(metadata.get("source_excerpt") or state["latest_user_message"])[:1000],
                confidence=confidence,
                extraction_method=(
                    "EDIT_COMPLAINT"
                    if is_edit
                    else "DOCUMENT_EXTRACTION"
                    if is_document
                    else "LOG_COMPLAINT"
                ),
                is_explicit=bool(metadata.get("explicitly_stated", True)),
                is_active=True,
            )
            field_evidence.append(
                {
                    "id": evidence.id,
                    "field_name": field_name,
                    "source_message_id": user_message_id,
                    "confidence": str(confidence) if confidence is not None else None,
                }
            )
            audit_repository.append(
                draft_id=draft.id,
                event_type=(
                    "EDIT_COMPLAINT_FIELD_CHANGED"
                    if is_edit
                    else "DOCUMENT_EXTRACTION_FIELD_CHANGED"
                    if is_document
                    else "LOG_COMPLAINT_FIELD_CHANGED"
                ),
                actor_type=ActorType.AI_AGENT,
                actor_identifier="Complaint Intake Assistant",
                tool_name="EDIT_COMPLAINT" if is_edit else "EXTRACT_DOCUMENT" if is_document else "LOG_COMPLAINT",
                field_name=field_name,
                old_value={"value": _serialise_value(old_value)},
                new_value={"value": _serialise_value(new_value)},
                reason=(
                    "User correction through AI Complaint Intake Assistant"
                    if is_edit
                    else "Document extraction through AI Complaint Intake Assistant"
                    if is_document
                    else "Initial complaint extraction"
                ),
                provider_name=state["provider"],
                requested_model=state["requested_model"],
                actual_model=state["actual_model"],
                metadata_json={
                    "source": "user_correction" if is_edit else "document_upload" if is_document else "user_message",
                    "source_message_id": user_message_id,
                    "source_attachment_id": metadata.get("attachment_id"),
                    "request_id": state["request_id"],
                    "operation": metadata.get("operation", "SET"),
                },
            )

        if changed_fields:
            draft.updated_at = utc_now()
        runtime.db.flush()
        refreshed = ComplaintDraftResponse.model_validate(draft).model_dump(mode="json")
        return {
            **state,
            "persisted_user_message": user_message,
            "pre_merge_complaint": pre_merge_complaint,
            "existing_complaint": refreshed,
            "changed_fields": changed_fields,
            "conflict_fields": conflict_fields,
            "no_op_fields": no_op_fields,
            "field_evidence": field_evidence,
            "warnings": warnings,
        }

    return node
