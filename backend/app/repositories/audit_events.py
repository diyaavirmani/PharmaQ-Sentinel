from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models import ActorType, AuditEvent
from app.models.base import utc_now
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class AuditEventRepository(BaseRepository[AuditEvent]):
    entity_name = "AuditEvent"

    def append(
        self,
        *,
        event_type: str,
        actor_type: ActorType,
        draft_id: str | None = None,
        complaint_id: str | None = None,
        actor_identifier: str | None = None,
        tool_name: str | None = None,
        field_name: str | None = None,
        old_value: dict[str, object] | None = None,
        new_value: dict[str, object] | None = None,
        reason: str | None = None,
        provider_name: str | None = None,
        requested_model: str | None = None,
        actual_model: str | None = None,
        metadata_json: dict[str, object] | None = None,
        created_at: datetime | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            draft_id=draft_id,
            complaint_id=complaint_id,
            event_type=event_type,
            actor_type=actor_type.value,
            actor_identifier=actor_identifier,
            tool_name=tool_name,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            provider_name=provider_name,
            requested_model=requested_model,
            actual_model=actual_model,
            metadata_json=metadata_json,
            created_at=created_at or utc_now(),
        )
        self.db.add(event)
        self.db.flush()
        return event

    def list_for_draft(
        self,
        draft_id: str,
        pagination: Pagination | None = None,
    ) -> list[AuditEvent]:
        statement = (
            select(AuditEvent)
            .where(AuditEvent.draft_id == draft_id)
            .order_by(AuditEvent.created_at.asc())
        )
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())
