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
            uploaded_by=uploaded_by,
            created_at=created_at or utc_now(),
        )
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def get(self, attachment_id: str) -> ComplaintAttachment | None:
        return self.db.get(ComplaintAttachment, attachment_id)

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
