from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Batch, Deviation, DuplicateAnalysisRun, HistoricalComplaint
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class DuplicateAnalysisRunRepository(BaseRepository[DuplicateAnalysisRun]):
    entity_name = "DuplicateAnalysisRun"

    def append(
        self,
        *,
        draft_id: str,
        input_snapshot: dict,
        result_json: dict,
        status: str,
        created_by: str | None,
    ) -> DuplicateAnalysisRun:
        run = DuplicateAnalysisRun(
            draft_id=draft_id,
            input_snapshot=input_snapshot,
            result_json=result_json,
            status=status,
            created_by=created_by,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def list_for_draft(self, draft_id: str, pagination: Pagination | None = None) -> list[DuplicateAnalysisRun]:
        statement = (
            select(DuplicateAnalysisRun)
            .where(DuplicateAnalysisRun.draft_id == draft_id)
            .order_by(DuplicateAnalysisRun.created_at.desc())
        )
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())


class DuplicateCandidateRepository(BaseRepository[HistoricalComplaint]):
    entity_name = "DuplicateCandidate"

    def list_historical_candidates(self, pagination: Pagination | None = None) -> list[HistoricalComplaint]:
        statement = (
            select(HistoricalComplaint)
            .options(
                selectinload(HistoricalComplaint.product),
                selectinload(HistoricalComplaint.batch).selectinload(Batch.packaging_material_lots),
                selectinload(HistoricalComplaint.batch).selectinload(Batch.material_lots),
                selectinload(HistoricalComplaint.batch).selectinload(Batch.equipment_records),
                selectinload(HistoricalComplaint.batch).selectinload(Batch.deviations).selectinload(Deviation.capas),
            )
            .order_by(HistoricalComplaint.complaint_date.desc())
        )
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).unique().all())
