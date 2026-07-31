from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models import AgentRun
from app.models.base import utc_now
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class AgentRunRepository(BaseRepository[AgentRun]):
    entity_name = "AgentRun"

    def create_started(
        self,
        *,
        draft_id: str,
        request_id: str,
        intent: str = "UNKNOWN",
        tool_name: str | None = None,
        provider: str | None = None,
        requested_model: str | None = None,
        actual_model: str | None = None,
        input_summary: str | None = None,
        warnings_json: dict[str, object] | None = None,
        started_at: datetime | None = None,
    ) -> AgentRun:
        run = AgentRun(
            draft_id=draft_id,
            request_id=request_id,
            intent=intent,
            tool_name=tool_name,
            status="STARTED",
            provider=provider,
            requested_model=requested_model,
            actual_model=actual_model,
            input_summary=input_summary,
            warnings_json=warnings_json,
            started_at=started_at or utc_now(),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def mark_completed(
        self,
        run: AgentRun,
        *,
        intent: str,
        tool_name: str | None,
        status: str,
        provider: str | None = None,
        requested_model: str | None = None,
        actual_model: str | None = None,
        output_summary: str | None = None,
        warnings_json: dict[str, object] | None = None,
        errors_json: dict[str, object] | None = None,
        completed_at: datetime | None = None,
    ) -> AgentRun:
        completed = completed_at or utc_now()
        run.intent = intent
        run.tool_name = tool_name
        run.status = status
        run.provider = provider
        run.requested_model = requested_model
        run.actual_model = actual_model
        run.output_summary = output_summary
        run.warnings_json = warnings_json
        run.errors_json = errors_json
        run.completed_at = completed
        run.latency_ms = max(int((completed - run.started_at).total_seconds() * 1000), 0)
        self.db.flush()
        return run

    def list_for_draft(
        self,
        draft_id: str,
        pagination: Pagination | None = None,
    ) -> list[AgentRun]:
        statement = (
            select(AgentRun)
            .where(AgentRun.draft_id == draft_id)
            .order_by(AgentRun.started_at.desc())
        )
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())
