from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models import Complaint
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class ComplaintRepository(BaseRepository[Complaint]):
    entity_name = "Complaint"

    def create(
        self,
        *,
        complaint_number: str,
        committed_by: str,
        committed_at: datetime,
        **fields: object,
    ) -> Complaint:
        complaint = Complaint(
            complaint_number=complaint_number,
            committed_by=committed_by,
            committed_at=committed_at,
            **fields,
        )
        self.db.add(complaint)
        self.db.flush()
        return complaint

    def get(self, complaint_id: str) -> Complaint | None:
        return self.db.get(Complaint, complaint_id)

    def get_required(self, complaint_id: str) -> Complaint:
        return self.require(self.get(complaint_id), complaint_id)

    def get_by_complaint_number(self, complaint_number: str) -> Complaint | None:
        statement = select(Complaint).where(Complaint.complaint_number == complaint_number)
        return self.db.scalars(statement).first()

    def list(self, pagination: Pagination | None = None) -> list[Complaint]:
        statement = select(Complaint).order_by(Complaint.created_at.desc())
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())
