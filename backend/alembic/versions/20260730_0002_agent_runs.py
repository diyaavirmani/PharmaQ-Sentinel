"""Add complaint assistant agent run metadata.

Revision ID: 20260730_0002
Revises: 20260730_0001
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "20260730_0002"
down_revision: str | None = "20260730_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_KWARGS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("draft_id", mysql.CHAR(36), nullable=False),
        sa.Column("request_id", sa.String(length=150), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=False),
        sa.Column("tool_name", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("requested_model", sa.String(length=150), nullable=True),
        sa.Column("actual_model", sa.String(length=150), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("warnings_json", mysql.JSON(), nullable=True),
        sa.Column("errors_json", mysql.JSON(), nullable=True),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("completed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("id", mysql.CHAR(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_agent_runs_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_runs")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_agent_runs_draft_id"), "agent_runs", ["draft_id"])
    op.create_index(op.f("ix_agent_runs_intent"), "agent_runs", ["intent"])
    op.create_index(op.f("ix_agent_runs_request_id"), "agent_runs", ["request_id"])
    op.create_index(op.f("ix_agent_runs_started_at"), "agent_runs", ["started_at"])
    op.create_index(op.f("ix_agent_runs_status"), "agent_runs", ["status"])


def downgrade() -> None:
    op.drop_table("agent_runs")
