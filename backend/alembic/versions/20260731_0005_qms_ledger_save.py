"""Add QMS ledger save metadata.

Revision ID: 20260731_0005
Revises: 20260731_0004
Create Date: 2026-07-31 03:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "20260731_0005"
down_revision: str | None = "20260731_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "complaint_number_sequences",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint("next_number > 0", name=op.f("ck_complaint_number_sequences_next_number_positive")),
        sa.PrimaryKeyConstraint("year", name=op.f("pk_complaint_number_sequences")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.add_column("complaints", sa.Column("save_idempotency_key", sa.String(length=150), nullable=True))
    op.add_column("complaints", sa.Column("review_meaning", sa.String(length=500), nullable=True))
    op.add_column(
        "complaints",
        sa.Column(
            "missing_information_acknowledged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("complaints", sa.Column("unresolved_missing_information", mysql.JSON(), nullable=True))
    op.add_column("complaints", sa.Column("latest_risk_assessment_id", mysql.CHAR(length=36), nullable=True))
    op.create_unique_constraint(
        op.f("uq_complaints_save_idempotency_key"),
        "complaints",
        ["save_idempotency_key"],
    )
    op.create_index(op.f("ix_complaints_save_idempotency_key"), "complaints", ["save_idempotency_key"], unique=False)
    op.create_index(op.f("ix_complaints_customer_name"), "complaints", ["customer_name"], unique=False)
    op.create_index(op.f("ix_complaints_complaint_type"), "complaints", ["complaint_type"], unique=False)
    op.create_index(op.f("ix_complaints_suggested_severity"), "complaints", ["suggested_severity"], unique=False)
    op.create_index(op.f("ix_complaints_complaint_date"), "complaints", ["complaint_date"], unique=False)
    op.create_index(op.f("ix_complaints_committed_at"), "complaints", ["committed_at"], unique=False)
    op.create_foreign_key(
        op.f("fk_complaints_latest_risk_assessment_id_risk_assessment_versions"),
        "complaints",
        "risk_assessment_versions",
        ["latest_risk_assessment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("complaints", "missing_information_acknowledged", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_complaints_latest_risk_assessment_id_risk_assessment_versions"),
        "complaints",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_complaints_committed_at"), table_name="complaints")
    op.drop_index(op.f("ix_complaints_complaint_date"), table_name="complaints")
    op.drop_index(op.f("ix_complaints_suggested_severity"), table_name="complaints")
    op.drop_index(op.f("ix_complaints_complaint_type"), table_name="complaints")
    op.drop_index(op.f("ix_complaints_customer_name"), table_name="complaints")
    op.drop_index(op.f("ix_complaints_save_idempotency_key"), table_name="complaints")
    op.drop_constraint(op.f("uq_complaints_save_idempotency_key"), "complaints", type_="unique")
    op.drop_column("complaints", "latest_risk_assessment_id")
    op.drop_column("complaints", "unresolved_missing_information")
    op.drop_column("complaints", "missing_information_acknowledged")
    op.drop_column("complaints", "review_meaning")
    op.drop_column("complaints", "save_idempotency_key")
    op.drop_table("complaint_number_sequences")
