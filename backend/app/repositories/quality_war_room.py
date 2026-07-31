from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import QualityWarRoomEvent, QualityWarRoomRun
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class QualityWarRoomRunRepository(BaseRepository[QualityWarRoomRun]):
    entity_name = "QualityWarRoomRun"

    def append(
        self,
        *,
        run_id: str,
        draft_id: str,
        input_snapshot: dict,
        status: str,
        iteration_count: int,
        specialist_outputs_json: dict,
        auditor_output_json: dict,
        consensus_json: dict,
        provider: str | None,
        model: str | None,
        started_at,
        completed_at,
        error_summary: str | None = None,
    ) -> QualityWarRoomRun:
        run = QualityWarRoomRun(
            id=run_id,
            draft_id=draft_id,
            input_snapshot=input_snapshot,
            status=status,
            iteration_count=iteration_count,
            specialist_outputs_json=specialist_outputs_json,
            auditor_output_json=auditor_output_json,
            consensus_json=consensus_json,
            provider=provider,
            model=model,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=error_summary,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def get(self, run_id: str) -> QualityWarRoomRun | None:
        statement = (
            select(QualityWarRoomRun)
            .options(selectinload(QualityWarRoomRun.events))
            .where(QualityWarRoomRun.id == run_id)
        )
        return self.db.scalars(statement).first()

    def get_required(self, run_id: str) -> QualityWarRoomRun:
        return self.require(self.get(run_id), run_id)

    def list_for_draft(self, draft_id: str, pagination: Pagination | None = None) -> list[QualityWarRoomRun]:
        statement = (
            select(QualityWarRoomRun)
            .where(QualityWarRoomRun.draft_id == draft_id)
            .order_by(QualityWarRoomRun.started_at.desc())
        )
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())


class QualityWarRoomEventRepository(BaseRepository[QualityWarRoomEvent]):
    entity_name = "QualityWarRoomEvent"

    def append(
        self,
        *,
        run_id: str,
        event_type: str,
        agent_name: str | None,
        status: str,
        concise_message: str,
        evidence_ids: list[str] | None = None,
        created_at,
    ) -> QualityWarRoomEvent:
        event = QualityWarRoomEvent(
            run_id=run_id,
            event_type=event_type,
            agent_name=agent_name,
            status=status,
            concise_message=concise_message,
            evidence_ids_json={"evidence_ids": evidence_ids or []},
            created_at=created_at,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def list_for_run(self, run_id: str) -> list[QualityWarRoomEvent]:
        statement = (
            select(QualityWarRoomEvent)
            .where(QualityWarRoomEvent.run_id == run_id)
            .order_by(QualityWarRoomEvent.created_at.asc(), QualityWarRoomEvent.id.asc())
        )
        return list(self.db.scalars(statement).all())
