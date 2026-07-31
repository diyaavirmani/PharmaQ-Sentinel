"""Add partial complaint date text fields.

Revision ID: 20260730_0003
Revises: 20260730_0002
Create Date: 2026-07-30 00:03:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260730_0003"
down_revision: str | None = "20260730_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("complaint_drafts", sa.Column("manufacturing_date_text", sa.String(length=100), nullable=True))
    op.add_column("complaint_drafts", sa.Column("expiry_retest_date_text", sa.String(length=100), nullable=True))
    op.add_column("complaints", sa.Column("manufacturing_date_text", sa.String(length=100), nullable=True))
    op.add_column("complaints", sa.Column("expiry_retest_date_text", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("complaints", "expiry_retest_date_text")
    op.drop_column("complaints", "manufacturing_date_text")
    op.drop_column("complaint_drafts", "expiry_retest_date_text")
    op.drop_column("complaint_drafts", "manufacturing_date_text")
