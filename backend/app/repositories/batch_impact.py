from __future__ import annotations

from sqlalchemy import select

from app.models import BatchImpactRun
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class BatchImpactRunRepository(BaseRepository[BatchImpactRun]):
    entity_name = "BatchImpactRun"

    def append(
        self,
        *,
        draft_id: str,
        input_snapshot: dict,
        graph_snapshot: dict,
        signals_json: dict,
        summary_json: dict,
        limitations_json: dict,
        created_by: str | None,
        provider: str | None,
        model: str | None,
        status: str,
    ) -> BatchImpactRun:
        run = BatchImpactRun(
            draft_id=draft_id,
            input_snapshot=input_snapshot,
            graph_snapshot=graph_snapshot,
            signals_json=signals_json,
            summary_json=summary_json,
            limitations_json=limitations_json,
            created_by=created_by,
            provider=provider,
            model=model,
            status=status,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def get(self, run_id: str) -> BatchImpactRun | None:
        return self.db.get(BatchImpactRun, run_id)

    def list_for_draft(
        self,
        draft_id: str,
        pagination: Pagination | None = None,
    ) -> list[BatchImpactRun]:
        statement = (
            select(BatchImpactRun)
            .where(BatchImpactRun.draft_id == draft_id)
            .order_by(BatchImpactRun.created_at.desc())
        )
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())
