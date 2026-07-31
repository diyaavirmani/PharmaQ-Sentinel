from __future__ import annotations

from sqlalchemy import select

from app.models import InvestigationPlaybookRun, InvestigationReviewAction
from app.repositories.base import BaseRepository, Pagination, apply_pagination


class InvestigationPlaybookRunRepository(BaseRepository[InvestigationPlaybookRun]):
    entity_name = "InvestigationPlaybookRun"

    def append(
        self,
        *,
        draft_id: str,
        input_snapshot: dict,
        playbook_json: dict,
        status: str,
        created_by: str | None,
    ) -> InvestigationPlaybookRun:
        run = InvestigationPlaybookRun(
            draft_id=draft_id,
            input_snapshot=input_snapshot,
            playbook_json=playbook_json,
            status=status,
            created_by=created_by,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def list_for_draft(self, draft_id: str, pagination: Pagination | None = None) -> list[InvestigationPlaybookRun]:
        statement = (
            select(InvestigationPlaybookRun)
            .where(InvestigationPlaybookRun.draft_id == draft_id)
            .order_by(InvestigationPlaybookRun.created_at.desc())
        )
        if pagination is not None:
            statement = apply_pagination(statement, pagination)
        return list(self.db.scalars(statement).all())


class InvestigationReviewActionRepository(BaseRepository[InvestigationReviewAction]):
    entity_name = "InvestigationReviewAction"

    def append(
        self,
        *,
        draft_id: str,
        run_id: str | None,
        action_type: str,
        target_type: str,
        target_id: str | None,
        original_text_json: dict | None,
        saved_text: str | None,
        reason: str | None,
        actor_identifier: str | None,
    ) -> InvestigationReviewAction:
        action = InvestigationReviewAction(
            draft_id=draft_id,
            run_id=run_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            original_text_json=original_text_json,
            saved_text=saved_text,
            reason=reason,
            actor_identifier=actor_identifier,
        )
        self.db.add(action)
        self.db.flush()
        return action
