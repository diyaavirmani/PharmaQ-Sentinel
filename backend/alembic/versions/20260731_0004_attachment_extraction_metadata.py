"""Add attachment extraction progress metadata.

Revision ID: 20260731_0004
Revises: 20260730_0003
Create Date: 2026-07-31 00:04:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "20260731_0004"
down_revision: str | None = "20260730_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("complaint_attachments", sa.Column("extraction_metadata", mysql.JSON(), nullable=True))
    op.add_column(
        "complaint_attachments",
        sa.Column("extraction_stage", sa.String(length=40), nullable=False, server_default="UPLOADING"),
    )
    op.add_column(
        "complaint_attachments",
        sa.Column("extraction_progress", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("complaint_attachments", sa.Column("completed_at", mysql.DATETIME(fsp=6), nullable=True))
    op.alter_column("complaint_attachments", "extraction_stage", server_default=None)
    op.alter_column("complaint_attachments", "extraction_progress", server_default=None)


def downgrade() -> None:
    op.drop_column("complaint_attachments", "completed_at")
    op.drop_column("complaint_attachments", "extraction_progress")
    op.drop_column("complaint_attachments", "extraction_stage")
    op.drop_column("complaint_attachments", "extraction_metadata")
