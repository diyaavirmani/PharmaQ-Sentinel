from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models import ComplaintVersion
from app.repositories.base import BaseRepository


class ComplaintVersionRepository(BaseRepository[ComplaintVersion]):
    entity_name = "ComplaintVersion"

    def append(
        self,
        *,
        complaint_id: str,
        version_number: int,
        snapshot: dict[str, object],
        checksum: str,
        created_by: str,
        created_at: datetime,
        change_reason: str | None = None,
    ) -> ComplaintVersion:
        version = ComplaintVersion(
            complaint_id=complaint_id,
            version_number=version_number,
            snapshot=snapshot,
            checksum=checksum,
            created_by=created_by,
            created_at=created_at,
            change_reason=change_reason,
        )
        self.db.add(version)
        self.db.flush()
        return version

    def get_latest_for_complaint(self, complaint_id: str) -> ComplaintVersion | None:
        statement = (
            select(ComplaintVersion)
            .where(ComplaintVersion.complaint_id == complaint_id)
            .order_by(ComplaintVersion.version_number.desc())
        )
        return self.db.scalars(statement).first()

    def list_for_complaint(self, complaint_id: str) -> list[ComplaintVersion]:
        statement = (
            select(ComplaintVersion)
            .where(ComplaintVersion.complaint_id == complaint_id)
            .order_by(ComplaintVersion.version_number.asc())
        )
        return list(self.db.scalars(statement).all())
