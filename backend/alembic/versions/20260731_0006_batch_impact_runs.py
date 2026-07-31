"""Add batch impact run persistence.

Revision ID: 20260731_0006
Revises: 20260731_0005
Create Date: 2026-07-31 09:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "20260731_0006"
down_revision: str | None = "20260731_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "batch_impact_runs",
        sa.Column("id", mysql.CHAR(length=36), nullable=False),
        sa.Column("draft_id", mysql.CHAR(length=36), nullable=False),
        sa.Column("input_snapshot", mysql.JSON(), nullable=False),
        sa.Column("graph_snapshot", mysql.JSON(), nullable=False),
        sa.Column("signals_json", mysql.JSON(), nullable=False),
        sa.Column("summary_json", mysql.JSON(), nullable=False),
        sa.Column("limitations_json", mysql.JSON(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("created_by", sa.String(length=150), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_batch_impact_runs_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_batch_impact_runs")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(op.f("ix_batch_impact_runs_created_at"), "batch_impact_runs", ["created_at"], unique=False)
    op.create_index(op.f("ix_batch_impact_runs_draft_id"), "batch_impact_runs", ["draft_id"], unique=False)
    op.create_index(op.f("ix_batch_impact_runs_status"), "batch_impact_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("batch_impact_runs")
