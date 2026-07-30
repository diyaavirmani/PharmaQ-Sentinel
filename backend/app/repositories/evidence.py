from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import EvidenceType, FieldEvidence
from app.models.base import utc_now
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class FieldEvidenceRepository(BaseRepository[FieldEvidence]):
    entity_name = "FieldEvidence"

    def add(
        self,
        *,
        draft_id: str,
        field_name: str,
        field_value: dict[str, object] | None,
        evidence_type: EvidenceType,
        source_attachment_id: str | None = None,
        source_message_id: str | None = None,
        source_excerpt: str | None = None,
        confidence: Decimal | None = None,
        extraction_method: str | None = None,
        is_explicit: bool = True,
        is_active: bool = True,
        page_number: int | None = None,
        paragraph_index: int | None = None,
        created_at: datetime | None = None,
    ) -> FieldEvidence:
        evidence = FieldEvidence(
            draft_id=draft_id,
            field_name=field_name,
            field_value=field_value,
            evidence_type=evidence_type.value,
            source_attachment_id=source_attachment_id,
            source_message_id=source_message_id,
            page_number=page_number,
            paragraph_index=paragraph_index,
            source_excerpt=source_excerpt,
            confidence=confidence,
            extraction_method=extraction_method,
            is_explicit=is_explicit,
            is_active=is_active,
            created_at=created_at or utc_now(),
        )
        self.db.add(evidence)
        self.db.flush()
        return evidence

    def list_for_draft(
        self,
        draft_id: str,
        pagination: Pagination | None = None,
    ) -> list[FieldEvidence]:
        statement = (
            select(FieldEvidence)
            .where(FieldEvidence.draft_id == draft_id)
            .order_by(FieldEvidence.created_at.asc())
        )
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())
