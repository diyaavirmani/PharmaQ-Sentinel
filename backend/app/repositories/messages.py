from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models import ComplaintMessage, MessageRole
from app.models.base import utc_now
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class ComplaintMessageRepository(BaseRepository[ComplaintMessage]):
    entity_name = "ComplaintMessage"

    def add(
        self,
        *,
        draft_id: str,
        role: MessageRole,
        message_text: str,
        attachment_id: str | None = None,
        metadata_json: dict[str, object] | None = None,
        created_at: datetime | None = None,
    ) -> ComplaintMessage:
        message = ComplaintMessage(
            draft_id=draft_id,
            role=role.value,
            message_text=message_text,
            attachment_id=attachment_id,
            metadata_json=metadata_json,
            created_at=created_at or utc_now(),
        )
        self.db.add(message)
        self.db.flush()
        return message

    def list_for_draft(
        self,
        draft_id: str,
        pagination: Pagination | None = None,
        before: datetime | None = None,
    ) -> list[ComplaintMessage]:
        statement = (
            select(ComplaintMessage)
            .where(ComplaintMessage.draft_id == draft_id)
            .order_by(ComplaintMessage.created_at.asc())
        )
        if before is not None:
            statement = statement.where(ComplaintMessage.created_at < before)
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())
