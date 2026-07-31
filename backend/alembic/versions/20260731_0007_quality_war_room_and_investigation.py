"""Add quality war room and investigation support runs.

Revision ID: 20260731_0007
Revises: 20260731_0006
Create Date: 2026-07-31 16:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "20260731_0007"
down_revision: str | None = "20260731_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quality_war_room_runs",
        sa.Column("id", mysql.CHAR(length=36), nullable=False),
        sa.Column("draft_id", mysql.CHAR(length=36), nullable=False),
        sa.Column("input_snapshot", mysql.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("iteration_count", sa.Integer(), nullable=False),
        sa.Column("specialist_outputs_json", mysql.JSON(), nullable=False),
        sa.Column("auditor_output_json", mysql.JSON(), nullable=False),
        sa.Column("consensus_json", mysql.JSON(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=150), nullable=True),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_quality_war_room_runs_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quality_war_room_runs")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(op.f("ix_quality_war_room_runs_draft_id"), "quality_war_room_runs", ["draft_id"], unique=False)
    op.create_index(op.f("ix_quality_war_room_runs_started_at"), "quality_war_room_runs", ["started_at"], unique=False)
    op.create_index(op.f("ix_quality_war_room_runs_status"), "quality_war_room_runs", ["status"], unique=False)

    op.create_table(
        "quality_war_room_events",
        sa.Column("id", mysql.CHAR(length=36), nullable=False),
        sa.Column("run_id", mysql.CHAR(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("concise_message", sa.String(length=500), nullable=False),
        sa.Column("evidence_ids_json", mysql.JSON(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["quality_war_room_runs.id"],
            name=op.f("fk_quality_war_room_events_run_id_quality_war_room_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quality_war_room_events")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(op.f("ix_quality_war_room_events_created_at"), "quality_war_room_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_quality_war_room_events_event_type"), "quality_war_room_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_quality_war_room_events_run_id"), "quality_war_room_events", ["run_id"], unique=False)

    op.create_table(
        "duplicate_analysis_runs",
        sa.Column("id", mysql.CHAR(length=36), nullable=False),
        sa.Column("draft_id", mysql.CHAR(length=36), nullable=False),
        sa.Column("input_snapshot", mysql.JSON(), nullable=False),
        sa.Column("result_json", mysql.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("created_by", sa.String(length=150), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_duplicate_analysis_runs_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_duplicate_analysis_runs")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(op.f("ix_duplicate_analysis_runs_created_at"), "duplicate_analysis_runs", ["created_at"], unique=False)
    op.create_index(op.f("ix_duplicate_analysis_runs_draft_id"), "duplicate_analysis_runs", ["draft_id"], unique=False)
    op.create_index(op.f("ix_duplicate_analysis_runs_status"), "duplicate_analysis_runs", ["status"], unique=False)

    op.create_table(
        "investigation_playbook_runs",
        sa.Column("id", mysql.CHAR(length=36), nullable=False),
        sa.Column("draft_id", mysql.CHAR(length=36), nullable=False),
        sa.Column("input_snapshot", mysql.JSON(), nullable=False),
        sa.Column("playbook_json", mysql.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("created_by", sa.String(length=150), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_investigation_playbook_runs_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation_playbook_runs")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(op.f("ix_investigation_playbook_runs_created_at"), "investigation_playbook_runs", ["created_at"], unique=False)
    op.create_index(op.f("ix_investigation_playbook_runs_draft_id"), "investigation_playbook_runs", ["draft_id"], unique=False)
    op.create_index(op.f("ix_investigation_playbook_runs_status"), "investigation_playbook_runs", ["status"], unique=False)

    op.create_table(
        "investigation_review_actions",
        sa.Column("id", mysql.CHAR(length=36), nullable=False),
        sa.Column("draft_id", mysql.CHAR(length=36), nullable=False),
        sa.Column("run_id", mysql.CHAR(length=36), nullable=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=150), nullable=True),
        sa.Column("original_text_json", mysql.JSON(), nullable=True),
        sa.Column("saved_text", sa.Text(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("actor_identifier", sa.String(length=150), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_investigation_review_actions_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation_review_actions")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(op.f("ix_investigation_review_actions_created_at"), "investigation_review_actions", ["created_at"], unique=False)
    op.create_index(op.f("ix_investigation_review_actions_draft_id"), "investigation_review_actions", ["draft_id"], unique=False)
    op.create_index(op.f("ix_investigation_review_actions_run_id"), "investigation_review_actions", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_table("investigation_review_actions")
    op.drop_table("investigation_playbook_runs")
    op.drop_table("duplicate_analysis_runs")
    op.drop_table("quality_war_room_events")
    op.drop_table("quality_war_room_runs")
