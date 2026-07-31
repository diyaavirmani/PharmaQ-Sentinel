from __future__ import annotations

from datetime import date, datetime

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

    def get_by_save_idempotency_key(self, idempotency_key: str) -> Complaint | None:
        statement = select(Complaint).where(Complaint.save_idempotency_key == idempotency_key)
        return self.db.scalars(statement).first()

    def get_by_committed_from_draft_id(self, draft_id: str) -> Complaint | None:
        statement = select(Complaint).where(Complaint.committed_from_draft_id == draft_id)
        return self.db.scalars(statement).first()

    def list(
        self,
        pagination: Pagination | None = None,
        *,
        complaint_number: str | None = None,
        product_name: str | None = None,
        batch_number: str | None = None,
        customer: str | None = None,
        complaint_type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Complaint]:
        statement = select(Complaint).order_by(Complaint.created_at.desc())
        if complaint_number:
            statement = statement.where(Complaint.complaint_number.like(f"%{complaint_number}%"))
        if product_name:
            statement = statement.where(Complaint.product_name.like(f"%{product_name}%"))
        if batch_number:
            statement = statement.where(Complaint.batch_lot_number == batch_number)
        if customer:
            statement = statement.where(Complaint.customer_name.like(f"%{customer}%"))
        if complaint_type:
            statement = statement.where(Complaint.complaint_type == complaint_type)
        if severity:
            statement = statement.where(Complaint.suggested_severity == severity)
        if status:
            statement = statement.where(Complaint.status == status)
        if date_from:
            statement = statement.where(Complaint.complaint_date >= date_from)
        if date_to:
            statement = statement.where(Complaint.complaint_date <= date_to)
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())
