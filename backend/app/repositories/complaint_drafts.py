from __future__ import annotations

from sqlalchemy import select

from app.models import ComplaintDraft
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class ComplaintDraftRepository(BaseRepository[ComplaintDraft]):
    entity_name = "ComplaintDraft"

    def create(self, *, thread_id: str, created_by: str | None = None, **fields: object) -> ComplaintDraft:
        draft = ComplaintDraft(thread_id=thread_id, created_by=created_by, **fields)
        self.db.add(draft)
        self.db.flush()
        return draft

    def get(self, draft_id: str) -> ComplaintDraft | None:
        return self.db.get(ComplaintDraft, draft_id)

    def get_required(self, draft_id: str) -> ComplaintDraft:
        return self.require(self.get(draft_id), draft_id)

    def get_by_thread_id(self, thread_id: str) -> ComplaintDraft | None:
        statement = select(ComplaintDraft).where(ComplaintDraft.thread_id == thread_id)
        return self.db.scalars(statement).first()

    def list(self, pagination: Pagination | None = None) -> list[ComplaintDraft]:
        statement = select(ComplaintDraft).order_by(ComplaintDraft.created_at.desc())
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())
