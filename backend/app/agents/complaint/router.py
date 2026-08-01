from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from sqlalchemy.orm import Session

from app.agents.complaint.graph import run_complaint_assistant
from app.agents.complaint.schemas import (
    ComplaintAssistantMessageRequest,
    ComplaintAssistantMessageResponse,
    ComplaintMessageListResponse,
    ComplaintMessageResponse,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import PharmaQSentinelError
from app.models import ActorType, ComplaintStatus, ExtractionStatus
from app.models.base import utc_now
from app.repositories import (
    AuditEventRepository,
    ComplaintAttachmentRepository,
    ComplaintDraftRepository,
    ComplaintMessageRepository,
    Pagination,
)
from app.schemas.complaints import (
    ComplaintAttachmentStatusResponse,
    ComplaintAttachmentUploadResponse,
    ComplaintDraftResponse,
)
from app.services.documents import DocumentParserRegistry
from app.services.documents.security import (
    detect_mime,
    ensure_safe_child_path,
    safe_stored_filename,
    sanitize_filename,
    sha256_bytes,
)

router = APIRouter(prefix="/complaint-drafts", tags=["complaint-assistant"])
LOCKED_DRAFT_STATUSES = {
    ComplaintStatus.COMMITTED.value,
    ComplaintStatus.CLOSED.value,
    ComplaintStatus.CANCELLED.value,
}


def _attachment_status_response(
    attachment,
    *,
    duplicate: bool = False,
    changed_fields: list[str] | None = None,
    draft=None,
) -> ComplaintAttachmentUploadResponse:
    return ComplaintAttachmentUploadResponse(
        attachment_id=attachment.id,
        original_filename=attachment.original_filename,
        status=attachment.extraction_status,
        progress_percentage=attachment.extraction_progress,
        current_stage=attachment.extraction_stage,
        duplicate=duplicate,
        changed_fields=changed_fields or [],
        created_at=attachment.created_at,
        draft=ComplaintDraftResponse.model_validate(draft) if draft is not None else None,
    )


def _safe_status_response(attachment) -> ComplaintAttachmentStatusResponse:
    return ComplaintAttachmentStatusResponse(
        attachment_id=attachment.id,
        original_filename=attachment.original_filename,
        status=attachment.extraction_status,
        progress_percentage=attachment.extraction_progress,
        current_stage=attachment.extraction_stage,
        safe_error=attachment.extraction_error,
        created_at=attachment.created_at,
        completed_at=attachment.completed_at,
    )


@router.post("/{draft_id}/messages", response_model=ComplaintAssistantMessageResponse)
def create_complaint_assistant_message(
    draft_id: str,
    request: ComplaintAssistantMessageRequest,
    db: Annotated[Session, Depends(get_db)],
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> ComplaintAssistantMessageResponse:
    request_id = x_request_id or str(uuid4())
    ComplaintDraftRepository(db).get_required(draft_id)
    try:
        state = run_complaint_assistant(
            db=db,
            draft_id=draft_id,
            request_id=request_id,
            latest_user_message=request.message,
            attachment_id=request.attachment_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    draft = ComplaintDraftRepository(db).get_required(draft_id)
    return ComplaintAssistantMessageResponse(
        user_message=ComplaintMessageResponse.model_validate(state["persisted_user_message"]),
        assistant_message=ComplaintMessageResponse.model_validate(state["persisted_assistant_message"]),
        intent=state["intent"],
        tool_name=state.get("tool_name"),
        draft=ComplaintDraftResponse.model_validate(draft),
        changed_fields=state["changed_fields"],
        warnings=state["warnings"],
        clarification_required=state["clarification_required"],
    )


@router.post("/{draft_id}/attachments", response_model=ComplaintAttachmentUploadResponse)
async def upload_complaint_attachment(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> ComplaintAttachmentUploadResponse:
    request_id = x_request_id or str(uuid4())
    settings = get_settings()
    draft = ComplaintDraftRepository(db).get_required(draft_id)
    if draft.status in LOCKED_DRAFT_STATUSES:
        raise PharmaQSentinelError("Complaint draft is locked and cannot accept uploads", status_code=409)

    original_filename = sanitize_filename(file.filename or "uploaded-document")
    content = await file.read()
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    if not content:
        raise PharmaQSentinelError("Uploaded file is empty", status_code=422)
    if len(content) > max_size_bytes:
        raise PharmaQSentinelError("Uploaded file exceeds the configured size limit", status_code=422)

    mime_type = detect_mime(content, original_filename)
    checksum = sha256_bytes(content)
    attachment_repository = ComplaintAttachmentRepository(db)
    duplicate = attachment_repository.get_by_hash_for_draft(draft_id, checksum)
    if duplicate:
        return _attachment_status_response(duplicate, duplicate=True, draft=draft)

    upload_directory = Path(settings.upload_directory)
    if not upload_directory.is_absolute():
        upload_directory = Path(__file__).resolve().parents[4] / upload_directory
    upload_directory.mkdir(parents=True, exist_ok=True)
    stored_filename = safe_stored_filename(original_filename)
    storage_path = ensure_safe_child_path(upload_directory, stored_filename)
    storage_path.write_bytes(content)

    audit_repository = AuditEventRepository(db)
    attachment = attachment_repository.add(
        draft_id=draft_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        mime_type=mime_type,
        file_size=len(content),
        sha256_checksum=checksum,
        storage_path=str(storage_path),
        extraction_status=ExtractionStatus.VALIDATING,
        extraction_stage="VALIDATING",
        extraction_progress=20,
        uploaded_by="Demo User",
    )
    audit_repository.append(
        draft_id=draft_id,
        event_type="DOCUMENT_UPLOADED",
        actor_type=ActorType.USER,
        actor_identifier="Demo User",
        tool_name="EXTRACT_DOCUMENT",
        field_name=None,
        old_value=None,
        new_value={"attachment_id": attachment.id},
        reason="User uploaded a complaint source document",
        metadata_json={
            "request_id": request_id,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "file_size": len(content),
            "sha256_checksum": checksum,
        },
    )

    changed_fields: list[str] = []
    try:
        attachment_repository.update_extraction_state(
            attachment,
            status=ExtractionStatus.EXTRACTING,
            stage="EXTRACTING_TEXT",
            progress=45,
        )
        parser = DocumentParserRegistry().get_parser(mime_type)
        parsed = parser.parse(storage_path)
        attachment_repository.update_extraction_state(
            attachment,
            status=ExtractionStatus.EXTRACTING,
            stage="STRUCTURING_FIELDS",
            progress=65,
            extracted_text=parsed.text,
            metadata={
                "document_type": parsed.document_type,
                "detected_mime_type": parsed.detected_mime_type,
                "segments": [segment.model_dump(mode="json") for segment in parsed.segments],
                "parser_metadata": parsed.metadata,
                "warnings": parsed.warnings,
            },
        )
        audit_repository.append(
            draft_id=draft_id,
            event_type="DOCUMENT_TEXT_EXTRACTED",
            actor_type=ActorType.SYSTEM,
            actor_identifier="Document Extraction Service",
            tool_name="DOCUMENT_TEXT_EXTRACTOR",
            field_name=None,
            old_value=None,
            new_value={"attachment_id": attachment.id, "character_count": len(parsed.text)},
            reason="Derived text was extracted from preserved source document",
            metadata_json={
                "request_id": request_id,
                "document_type": parsed.document_type,
                "segment_count": len(parsed.segments),
                "warnings": parsed.warnings,
            },
        )
        state = run_complaint_assistant(
            db=db,
            draft_id=draft_id,
            request_id=request_id,
            latest_user_message=f"Uploaded complaint document: {original_filename}",
            attachment_id=attachment.id,
        )
        changed_fields = state["changed_fields"]
        db.commit()
    except PharmaQSentinelError as exc:
        attachment_repository.update_extraction_state(
            attachment,
            status=ExtractionStatus.FAILED,
            stage="FAILED",
            progress=100,
            error=exc.message,
            completed_at=utc_now(),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(attachment)
    refreshed_draft = ComplaintDraftRepository(db).get_required(draft_id)
    return _attachment_status_response(attachment, changed_fields=changed_fields, draft=refreshed_draft)


@router.get("/{draft_id}/attachments/{attachment_id}/status", response_model=ComplaintAttachmentStatusResponse)
def get_complaint_attachment_status(
    draft_id: str,
    attachment_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ComplaintAttachmentStatusResponse:
    ComplaintDraftRepository(db).get_required(draft_id)
    attachment = ComplaintAttachmentRepository(db).get_for_draft(draft_id, attachment_id)
    if attachment is None:
        raise PharmaQSentinelError("Complaint attachment was not found", status_code=404)
    return _safe_status_response(attachment)


@router.get("/{draft_id}/messages", response_model=ComplaintMessageListResponse)
def list_complaint_assistant_messages(
    draft_id: str,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    before: Annotated[datetime | None, Query()] = None,
) -> ComplaintMessageListResponse:
    ComplaintDraftRepository(db).get_required(draft_id)
    pagination = Pagination(limit=limit, offset=offset)
    messages = ComplaintMessageRepository(db).list_for_draft(draft_id, pagination, before=before)
    next_offset = offset + limit if len(messages) == limit else None
    return ComplaintMessageListResponse(
        messages=[ComplaintMessageResponse.model_validate(message) for message in messages],
        limit=limit,
        offset=offset,
        next_offset=next_offset,
    )
