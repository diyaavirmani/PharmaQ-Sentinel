from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models import ComplaintAttachment, ExtractionStatus
from app.models.base import utc_now
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class ComplaintAttachmentRepository(BaseRepository[ComplaintAttachment]):
    entity_name = "ComplaintAttachment"

    def add(
        self,
        *,
        draft_id: str,
        original_filename: str,
        stored_filename: str,
        mime_type: str,
        file_size: int,
        sha256_checksum: str,
        storage_path: str,
        extraction_status: ExtractionStatus = ExtractionStatus.PENDING,
        extraction_stage: str = "UPLOADING",
        extraction_progress: int = 0,
        uploaded_by: str | None = None,
        created_at: datetime | None = None,
    ) -> ComplaintAttachment:
        attachment = ComplaintAttachment(
            draft_id=draft_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            mime_type=mime_type,
            file_size=file_size,
            sha256_checksum=sha256_checksum,
            storage_path=storage_path,
            extraction_status=extraction_status.value,
            extraction_stage=extraction_stage,
            extraction_progress=extraction_progress,
            uploaded_by=uploaded_by,
            created_at=created_at or utc_now(),
        )
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def get(self, attachment_id: str) -> ComplaintAttachment | None:
        return self.db.get(ComplaintAttachment, attachment_id)

    def get_for_draft(self, draft_id: str, attachment_id: str) -> ComplaintAttachment | None:
        statement = select(ComplaintAttachment).where(
            ComplaintAttachment.id == attachment_id,
            ComplaintAttachment.draft_id == draft_id,
        )
        return self.db.scalars(statement).first()

    def get_by_hash_for_draft(self, draft_id: str, sha256_checksum: str) -> ComplaintAttachment | None:
        statement = select(ComplaintAttachment).where(
            ComplaintAttachment.draft_id == draft_id,
            ComplaintAttachment.sha256_checksum == sha256_checksum,
        )
        return self.db.scalars(statement).first()

    def update_extraction_state(
        self,
        attachment: ComplaintAttachment,
        *,
        status: ExtractionStatus | None = None,
        stage: str | None = None,
        progress: int | None = None,
        extracted_text: str | None = None,
        metadata: dict[str, object] | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> ComplaintAttachment:
        if status is not None:
            attachment.extraction_status = status.value
        if stage is not None:
            attachment.extraction_stage = stage
        if progress is not None:
            attachment.extraction_progress = progress
        if extracted_text is not None:
            attachment.extracted_text = extracted_text
        if metadata is not None:
            attachment.extraction_metadata = metadata
        if error is not None:
            attachment.extraction_error = error
        if completed_at is not None:
            attachment.completed_at = completed_at
        self.db.flush()
        return attachment

    def list_for_draft(
        self,
        draft_id: str,
        pagination: Pagination | None = None,
    ) -> list[ComplaintAttachment]:
        statement = (
            select(ComplaintAttachment)
            .where(ComplaintAttachment.draft_id == draft_id)
            .order_by(ComplaintAttachment.created_at.asc())
        )
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())
