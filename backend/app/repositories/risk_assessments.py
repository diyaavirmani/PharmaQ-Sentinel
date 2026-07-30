from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import Priority, RiskAssessmentVersion, Severity
from app.models.base import utc_now
from app.repositories.base import BaseRepository


class RiskAssessmentVersionRepository(BaseRepository[RiskAssessmentVersion]):
    entity_name = "RiskAssessmentVersion"

    def append(
        self,
        *,
        draft_id: str,
        version_number: int,
        severity: Severity,
        priority: Priority,
        risk_rationale: str,
        confidence: Decimal | None = None,
        created_at: datetime | None = None,
        **fields: object,
    ) -> RiskAssessmentVersion:
        version = RiskAssessmentVersion(
            draft_id=draft_id,
            version_number=version_number,
            severity=severity.value,
            priority=priority.value,
            risk_rationale=risk_rationale,
            confidence=confidence,
            created_at=created_at or utc_now(),
            **fields,
        )
        self.db.add(version)
        self.db.flush()
        return version

    def get_latest_for_draft(self, draft_id: str) -> RiskAssessmentVersion | None:
        statement = (
            select(RiskAssessmentVersion)
            .where(RiskAssessmentVersion.draft_id == draft_id)
            .order_by(RiskAssessmentVersion.version_number.desc())
        )
        return self.db.scalars(statement).first()

    def list_for_draft(self, draft_id: str) -> list[RiskAssessmentVersion]:
        statement = (
            select(RiskAssessmentVersion)
            .where(RiskAssessmentVersion.draft_id == draft_id)
            .order_by(RiskAssessmentVersion.version_number.asc())
        )
        return list(self.db.scalars(statement).all())
