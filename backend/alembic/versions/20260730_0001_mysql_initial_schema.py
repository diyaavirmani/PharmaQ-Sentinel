"""Create initial MySQL schema.

Revision ID: 20260730_0001
Revises:
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "20260730_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_KWARGS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"}


def uuid_pk() -> sa.Column:
    return sa.Column("id", mysql.CHAR(36), nullable=False)


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
    )


def demo_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("record_source", sa.String(length=40), nullable=False),
    )


def complaint_field_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("complaint_source", sa.String(length=150), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("customer_contact", sa.String(length=255), nullable=True),
        sa.Column("country_market", sa.String(length=150), nullable=True),
        sa.Column("product_type", sa.String(length=20), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("product_strength_grade", sa.String(length=150), nullable=True),
        sa.Column("dosage_form", sa.String(length=100), nullable=True),
        sa.Column("batch_lot_number", sa.String(length=150), nullable=True),
        sa.Column("manufacturing_date", sa.Date(), nullable=True),
        sa.Column("expiry_retest_date", sa.Date(), nullable=True),
        sa.Column("quantity_affected", sa.Numeric(14, 3), nullable=True),
        sa.Column("quantity_unit", sa.String(length=50), nullable=True),
        sa.Column("complaint_type", sa.String(length=150), nullable=True),
        sa.Column("complaint_date", sa.Date(), nullable=True),
        sa.Column("detailed_description", sa.Text(), nullable=True),
        sa.Column("defect_observed_date", sa.Date(), nullable=True),
        sa.Column("sample_available", sa.Boolean(), nullable=True),
        sa.Column("patient_consumed_product", sa.Boolean(), nullable=True),
        sa.Column("adverse_event_signal", sa.Boolean(), nullable=True),
        sa.Column("counterfeit_signal", sa.Boolean(), nullable=True),
        sa.Column("storage_conditions", sa.Text(), nullable=True),
        sa.Column("suggested_severity", sa.String(length=30), nullable=True),
        sa.Column("suggested_priority", sa.String(length=30), nullable=True),
        sa.Column("safety_route", sa.String(length=50), nullable=True),
        sa.Column("risk_rationale", sa.Text(), nullable=True),
        sa.Column("potential_hazard", sa.Text(), nullable=True),
        sa.Column("suggested_next_action", sa.Text(), nullable=True),
        sa.Column("risk_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("missing_fields", mysql.JSON(), nullable=True),
    )


def create_tables() -> None:
    op.create_table(
        "complaint_drafts",
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        uuid_pk(),
        *timestamp_columns(),
        sa.Column("created_by", sa.String(length=150), nullable=True),
        *complaint_field_columns(),
        sa.CheckConstraint(
            "quantity_affected IS NULL OR quantity_affected >= 0",
            name=op.f("ck_complaint_drafts_quantity_affected_non_negative"),
        ),
        sa.CheckConstraint(
            "risk_confidence IS NULL OR (risk_confidence >= 0 AND risk_confidence <= 1)",
            name=op.f("ck_complaint_drafts_risk_confidence_between_zero_and_one"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_complaint_drafts")),
        sa.UniqueConstraint("thread_id", name=op.f("uq_complaint_drafts_thread_id")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_complaint_drafts_batch_lot_number"), "complaint_drafts", ["batch_lot_number"])
    op.create_index(op.f("ix_complaint_drafts_complaint_type"), "complaint_drafts", ["complaint_type"])
    op.create_index(op.f("ix_complaint_drafts_created_at"), "complaint_drafts", ["created_at"])
    op.create_index(op.f("ix_complaint_drafts_status"), "complaint_drafts", ["status"])
    op.create_index(op.f("ix_complaint_drafts_suggested_severity"), "complaint_drafts", ["suggested_severity"])
    op.create_index(op.f("ix_complaint_drafts_thread_id"), "complaint_drafts", ["thread_id"])

    op.create_table(
        "manufacturing_lines",
        sa.Column("line_code", sa.String(length=80), nullable=False),
        sa.Column("line_name", sa.String(length=255), nullable=False),
        sa.Column("line_type", sa.String(length=80), nullable=False),
        sa.Column("manufacturing_site", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manufacturing_lines")),
        sa.UniqueConstraint("line_code", name=op.f("uq_manufacturing_lines_line_code")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_manufacturing_lines_line_type"), "manufacturing_lines", ["line_type"])

    op.create_table(
        "products",
        sa.Column("product_code", sa.String(length=80), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("product_type", sa.String(length=20), nullable=False),
        sa.Column("strength_grade", sa.String(length=150), nullable=True),
        sa.Column("dosage_form", sa.String(length=100), nullable=True),
        sa.Column("market_status", sa.String(length=80), nullable=True),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("product_code", name=op.f("uq_products_product_code")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_products_product_name"), "products", ["product_name"])
    op.create_index(op.f("ix_products_product_type"), "products", ["product_type"])

    op.create_table(
        "suppliers",
        sa.Column("supplier_code", sa.String(length=80), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("supplier_type", sa.String(length=80), nullable=False),
        sa.Column("qualification_status", sa.String(length=80), nullable=False),
        sa.Column("country", sa.String(length=150), nullable=True),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
        sa.UniqueConstraint("supplier_code", name=op.f("uq_suppliers_supplier_code")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_suppliers_supplier_name"), "suppliers", ["supplier_name"])

    op.create_table(
        "batches",
        sa.Column("batch_number", sa.String(length=150), nullable=False),
        sa.Column("product_id", mysql.CHAR(36), nullable=False),
        sa.Column("manufacturing_date", sa.Date(), nullable=True),
        sa.Column("expiry_retest_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("manufacturing_line_id", mysql.CHAR(36), nullable=True),
        sa.Column("packaging_line_id", mysql.CHAR(36), nullable=True),
        sa.Column("quantity_manufactured", sa.Numeric(14, 3), nullable=True),
        sa.Column("quantity_released", sa.Numeric(14, 3), nullable=True),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.CheckConstraint(
            "quantity_manufactured IS NULL OR quantity_manufactured >= 0",
            name=op.f("ck_batches_quantity_manufactured_non_negative"),
        ),
        sa.CheckConstraint(
            "quantity_released IS NULL OR quantity_released >= 0",
            name=op.f("ck_batches_quantity_released_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["manufacturing_line_id"],
            ["manufacturing_lines.id"],
            name=op.f("fk_batches_manufacturing_line_id_manufacturing_lines"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["packaging_line_id"],
            ["manufacturing_lines.id"],
            name=op.f("fk_batches_packaging_line_id_manufacturing_lines"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_batches_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_batches")),
        sa.UniqueConstraint("batch_number", name=op.f("uq_batches_batch_number")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_batches_batch_number"), "batches", ["batch_number"])
    op.create_index(op.f("ix_batches_status"), "batches", ["status"])

    op.create_table(
        "complaint_attachments",
        sa.Column("draft_id", mysql.CHAR(36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256_checksum", mysql.CHAR(64), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("extracted_text", mysql.LONGTEXT(), nullable=True),
        sa.Column("extraction_status", sa.String(length=40), nullable=False),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("uploaded_by", sa.String(length=150), nullable=True),
        uuid_pk(),
        sa.CheckConstraint("file_size >= 0", name=op.f("ck_complaint_attachments_file_size_non_negative")),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_complaint_attachments_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_complaint_attachments")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_complaint_attachments_draft_id"), "complaint_attachments", ["draft_id"])
    op.create_index(op.f("ix_complaint_attachments_extraction_status"), "complaint_attachments", ["extraction_status"])
    op.create_index(op.f("ix_complaint_attachments_sha256_checksum"), "complaint_attachments", ["sha256_checksum"])

    op.create_table(
        "complaints",
        sa.Column("complaint_number", sa.String(length=40), nullable=False),
        sa.Column("current_version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("committed_from_draft_id", mysql.CHAR(36), nullable=True),
        sa.Column("committed_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("committed_by", sa.String(length=150), nullable=False),
        uuid_pk(),
        *timestamp_columns(),
        *complaint_field_columns(),
        sa.CheckConstraint(
            "current_version_number > 0",
            name=op.f("ck_complaints_current_version_number_positive"),
        ),
        sa.CheckConstraint(
            "quantity_affected IS NULL OR quantity_affected >= 0",
            name=op.f("ck_complaints_quantity_affected_non_negative"),
        ),
        sa.CheckConstraint(
            "risk_confidence IS NULL OR (risk_confidence >= 0 AND risk_confidence <= 1)",
            name=op.f("ck_complaints_risk_confidence_between_zero_and_one"),
        ),
        sa.ForeignKeyConstraint(
            ["committed_from_draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_complaints_committed_from_draft_id_complaint_drafts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_complaints")),
        sa.UniqueConstraint("complaint_number", name=op.f("uq_complaints_complaint_number")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_complaints_batch_lot_number"), "complaints", ["batch_lot_number"])
    op.create_index(op.f("ix_complaints_complaint_number"), "complaints", ["complaint_number"])
    op.create_index(op.f("ix_complaints_product_name"), "complaints", ["product_name"])
    op.create_index(op.f("ix_complaints_status"), "complaints", ["status"])

    op.create_table(
        "equipment",
        sa.Column("equipment_code", sa.String(length=80), nullable=False),
        sa.Column("equipment_name", sa.String(length=255), nullable=False),
        sa.Column("equipment_type", sa.String(length=100), nullable=False),
        sa.Column("manufacturing_line_id", mysql.CHAR(36), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.ForeignKeyConstraint(
            ["manufacturing_line_id"],
            ["manufacturing_lines.id"],
            name=op.f("fk_equipment_manufacturing_line_id_manufacturing_lines"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_equipment")),
        sa.UniqueConstraint("equipment_code", name=op.f("uq_equipment_equipment_code")),
        **TABLE_KWARGS,
    )

    op.create_table(
        "material_lots",
        sa.Column("material_code", sa.String(length=80), nullable=False),
        sa.Column("material_name", sa.String(length=255), nullable=False),
        sa.Column("lot_number", sa.String(length=150), nullable=False),
        sa.Column("supplier_id", mysql.CHAR(36), nullable=True),
        sa.Column("material_type", sa.String(length=80), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("expiry_retest_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_material_lots_supplier_id_suppliers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_material_lots")),
        sa.UniqueConstraint("lot_number", name=op.f("uq_material_lots_lot_number")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_material_lots_lot_number"), "material_lots", ["lot_number"])
    op.create_index(op.f("ix_material_lots_material_code"), "material_lots", ["material_code"])

    op.create_table(
        "packaging_material_lots",
        sa.Column("packaging_material_code", sa.String(length=80), nullable=False),
        sa.Column("material_name", sa.String(length=255), nullable=False),
        sa.Column("lot_number", sa.String(length=150), nullable=False),
        sa.Column("supplier_id", mysql.CHAR(36), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_packaging_material_lots_supplier_id_suppliers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_packaging_material_lots")),
        sa.UniqueConstraint("lot_number", name=op.f("uq_packaging_material_lots_lot_number")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_packaging_material_lots_code"), "packaging_material_lots", ["packaging_material_code"])
    op.create_index(op.f("ix_packaging_material_lots_lot_number"), "packaging_material_lots", ["lot_number"])

    op.create_table(
        "risk_assessment_versions",
        sa.Column("draft_id", mysql.CHAR(36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.String(length=30), nullable=False),
        sa.Column("patient_harm_level", sa.String(length=30), nullable=True),
        sa.Column("safety_route", sa.String(length=50), nullable=True),
        sa.Column("risk_rationale", sa.Text(), nullable=False),
        sa.Column("potential_hazard", sa.Text(), nullable=True),
        sa.Column("suggested_next_action", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("supporting_evidence", mysql.JSON(), nullable=True),
        sa.Column("contradicting_evidence", mysql.JSON(), nullable=True),
        sa.Column("provider_name", sa.String(length=50), nullable=True),
        sa.Column("requested_model", sa.String(length=150), nullable=True),
        sa.Column("actual_model", sa.String(length=150), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        uuid_pk(),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name=op.f("ck_risk_assessment_versions_confidence_between_zero_and_one"),
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name=op.f("ck_risk_assessment_versions_version_number_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_risk_assessment_versions_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_assessment_versions")),
        sa.UniqueConstraint(
            "draft_id",
            "version_number",
            name=op.f("uq_risk_assessment_versions_draft_id_version_number"),
        ),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_risk_assessment_versions_draft_id"), "risk_assessment_versions", ["draft_id"])

    op.create_table(
        "audit_events",
        sa.Column("draft_id", mysql.CHAR(36), nullable=True),
        sa.Column("complaint_id", mysql.CHAR(36), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("actor_type", sa.String(length=30), nullable=False),
        sa.Column("actor_identifier", sa.String(length=150), nullable=True),
        sa.Column("tool_name", sa.String(length=150), nullable=True),
        sa.Column("field_name", sa.String(length=150), nullable=True),
        sa.Column("old_value", mysql.JSON(), nullable=True),
        sa.Column("new_value", mysql.JSON(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("provider_name", sa.String(length=50), nullable=True),
        sa.Column("requested_model", sa.String(length=150), nullable=True),
        sa.Column("actual_model", sa.String(length=150), nullable=True),
        sa.Column("metadata_json", mysql.JSON(), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        uuid_pk(),
        sa.ForeignKeyConstraint(
            ["complaint_id"],
            ["complaints.id"],
            name=op.f("fk_audit_events_complaint_id_complaints"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_audit_events_draft_id_complaint_drafts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_audit_events_complaint_id"), "audit_events", ["complaint_id"])
    op.create_index(op.f("ix_audit_events_created_at"), "audit_events", ["created_at"])
    op.create_index(op.f("ix_audit_events_draft_id"), "audit_events", ["draft_id"])
    op.create_index(op.f("ix_audit_events_event_type"), "audit_events", ["event_type"])

    op.create_table(
        "batch_material_lots",
        sa.Column("batch_id", mysql.CHAR(36), nullable=False),
        sa.Column("material_lot_id", mysql.CHAR(36), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], name="fk_bml_batch", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["material_lot_id"],
            ["material_lots.id"],
            name="fk_bml_material_lot",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("batch_id", "material_lot_id", name=op.f("pk_batch_material_lots")),
        sa.UniqueConstraint("batch_id", "material_lot_id", name="uq_batch_material_lots_pair"),
        **TABLE_KWARGS,
    )

    op.create_table(
        "batch_packaging_material_lots",
        sa.Column("batch_id", mysql.CHAR(36), nullable=False),
        sa.Column("packaging_material_lot_id", mysql.CHAR(36), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], name="fk_bpml_batch", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["packaging_material_lot_id"],
            ["packaging_material_lots.id"],
            name="fk_bpml_packaging_material_lot",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "batch_id",
            "packaging_material_lot_id",
            name=op.f("pk_batch_packaging_material_lots"),
        ),
        sa.UniqueConstraint("batch_id", "packaging_material_lot_id", name="uq_batch_packaging_lots_pair"),
        **TABLE_KWARGS,
    )

    op.create_table(
        "batch_equipment",
        sa.Column("batch_id", mysql.CHAR(36), nullable=False),
        sa.Column("equipment_id", mysql.CHAR(36), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], name="fk_be_batch", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], name="fk_be_equipment", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("batch_id", "equipment_id", name=op.f("pk_batch_equipment")),
        sa.UniqueConstraint("batch_id", "equipment_id", name="uq_batch_equipment_pair"),
        **TABLE_KWARGS,
    )

    op.create_table(
        "complaint_messages",
        sa.Column("draft_id", mysql.CHAR(36), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("message_text", mysql.LONGTEXT(), nullable=False),
        sa.Column("attachment_id", mysql.CHAR(36), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("metadata_json", mysql.JSON(), nullable=True),
        uuid_pk(),
        sa.ForeignKeyConstraint(
            ["attachment_id"],
            ["complaint_attachments.id"],
            name=op.f("fk_complaint_messages_attachment_id_complaint_attachments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_complaint_messages_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_complaint_messages")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_complaint_messages_created_at"), "complaint_messages", ["created_at"])
    op.create_index(op.f("ix_complaint_messages_draft_id"), "complaint_messages", ["draft_id"])

    op.create_table(
        "complaint_versions",
        sa.Column("complaint_id", mysql.CHAR(36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", mysql.JSON(), nullable=False),
        sa.Column("change_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("created_by", sa.String(length=150), nullable=False),
        sa.Column("checksum", mysql.CHAR(64), nullable=False),
        uuid_pk(),
        sa.CheckConstraint("CHAR_LENGTH(checksum) = 64", name=op.f("ck_complaint_versions_checksum_sha256_hex_length")),
        sa.CheckConstraint("version_number > 0", name=op.f("ck_complaint_versions_version_number_positive")),
        sa.ForeignKeyConstraint(
            ["complaint_id"],
            ["complaints.id"],
            name=op.f("fk_complaint_versions_complaint_id_complaints"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_complaint_versions")),
        sa.UniqueConstraint("complaint_id", "version_number", name=op.f("uq_complaint_versions_complaint_id_version_number")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_complaint_versions_complaint_id"), "complaint_versions", ["complaint_id"])

    op.create_table(
        "deviations",
        sa.Column("deviation_number", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("batch_id", mysql.CHAR(36), nullable=True),
        sa.Column("manufacturing_line_id", mysql.CHAR(36), nullable=True),
        sa.Column("equipment_id", mysql.CHAR(36), nullable=True),
        sa.Column("opened_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("closed_at", mysql.DATETIME(fsp=6), nullable=True),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name=op.f("fk_deviations_batch_id_batches"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipment.id"],
            name=op.f("fk_deviations_equipment_id_equipment"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["manufacturing_line_id"],
            ["manufacturing_lines.id"],
            name=op.f("fk_deviations_manufacturing_line_id_manufacturing_lines"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deviations")),
        sa.UniqueConstraint("deviation_number", name=op.f("uq_deviations_deviation_number")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_deviations_severity"), "deviations", ["severity"])
    op.create_index(op.f("ix_deviations_status"), "deviations", ["status"])

    op.create_table(
        "distribution_records",
        sa.Column("batch_id", mysql.CHAR(36), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("market_city", sa.String(length=150), nullable=False),
        sa.Column("market_state", sa.String(length=150), nullable=True),
        sa.Column("quantity_distributed", sa.Numeric(14, 3), nullable=False),
        sa.Column("shipment_date", sa.Date(), nullable=True),
        sa.Column("shipment_status", sa.String(length=80), nullable=False),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.CheckConstraint(
            "quantity_distributed >= 0",
            name=op.f("ck_distribution_records_quantity_distributed_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name=op.f("fk_distribution_records_batch_id_batches"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_distribution_records")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_distribution_records_batch_id"), "distribution_records", ["batch_id"])
    op.create_index(op.f("ix_distribution_records_market_city"), "distribution_records", ["market_city"])

    op.create_table(
        "historical_complaints",
        sa.Column("complaint_number", sa.String(length=40), nullable=False),
        sa.Column("product_id", mysql.CHAR(36), nullable=True),
        sa.Column("batch_id", mysql.CHAR(36), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("complaint_type", sa.String(length=150), nullable=False),
        sa.Column("detailed_description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("complaint_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("metadata_json", mysql.JSON(), nullable=True),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name=op.f("fk_historical_complaints_batch_id_batches"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_historical_complaints_product_id_products"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historical_complaints")),
        sa.UniqueConstraint("complaint_number", name=op.f("uq_historical_complaints_complaint_number")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_historical_complaints_batch_id"), "historical_complaints", ["batch_id"])
    op.create_index(op.f("ix_historical_complaints_complaint_date"), "historical_complaints", ["complaint_date"])
    op.create_index(op.f("ix_historical_complaints_complaint_type"), "historical_complaints", ["complaint_type"])
    op.create_index(op.f("ix_historical_complaints_product_id"), "historical_complaints", ["product_id"])
    op.create_index(op.f("ix_historical_complaints_severity"), "historical_complaints", ["severity"])

    op.create_table(
        "warehouse_inventory",
        sa.Column("batch_id", mysql.CHAR(36), nullable=False),
        sa.Column("warehouse_name", sa.String(length=180), nullable=False),
        sa.Column("quantity_available", sa.Numeric(14, 3), nullable=False),
        sa.Column("quantity_on_hold", sa.Numeric(14, 3), nullable=False),
        sa.Column("last_updated_at", mysql.DATETIME(fsp=6), nullable=False),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.CheckConstraint(
            "quantity_available >= 0",
            name=op.f("ck_warehouse_inventory_quantity_available_non_negative"),
        ),
        sa.CheckConstraint(
            "quantity_on_hold >= 0",
            name=op.f("ck_warehouse_inventory_quantity_on_hold_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["batches.id"],
            name=op.f("fk_warehouse_inventory_batch_id_batches"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_warehouse_inventory")),
        sa.UniqueConstraint("batch_id", "warehouse_name", name=op.f("uq_warehouse_inventory_batch_id_warehouse_name")),
        **TABLE_KWARGS,
    )

    op.create_table(
        "capas",
        sa.Column("capa_number", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("linked_deviation_id", mysql.CHAR(36), nullable=True),
        sa.Column("effectiveness_status", sa.String(length=100), nullable=True),
        sa.Column("opened_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("closed_at", mysql.DATETIME(fsp=6), nullable=True),
        uuid_pk(),
        *timestamp_columns(),
        *demo_columns(),
        sa.ForeignKeyConstraint(
            ["linked_deviation_id"],
            ["deviations.id"],
            name=op.f("fk_capas_linked_deviation_id_deviations"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capas")),
        sa.UniqueConstraint("capa_number", name=op.f("uq_capas_capa_number")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_capas_status"), "capas", ["status"])

    op.create_table(
        "field_evidence",
        sa.Column("draft_id", mysql.CHAR(36), nullable=False),
        sa.Column("field_name", sa.String(length=150), nullable=False),
        sa.Column("field_value", mysql.JSON(), nullable=True),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("source_attachment_id", mysql.CHAR(36), nullable=True),
        sa.Column("source_message_id", mysql.CHAR(36), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("paragraph_index", sa.Integer(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("extraction_method", sa.String(length=150), nullable=True),
        sa.Column("is_explicit", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        uuid_pk(),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name=op.f("ck_field_evidence_confidence_between_zero_and_one"),
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["complaint_drafts.id"],
            name=op.f("fk_field_evidence_draft_id_complaint_drafts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_attachment_id"],
            ["complaint_attachments.id"],
            name=op.f("fk_field_evidence_source_attachment_id_complaint_attachments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["complaint_messages.id"],
            name=op.f("fk_field_evidence_source_message_id_complaint_messages"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_field_evidence")),
        **TABLE_KWARGS,
    )
    op.create_index(op.f("ix_field_evidence_draft_id"), "field_evidence", ["draft_id"])
    op.create_index(op.f("ix_field_evidence_field_name"), "field_evidence", ["field_name"])


def upgrade() -> None:
    create_tables()


def downgrade() -> None:
    op.drop_table("field_evidence")
    op.drop_table("capas")
    op.drop_table("warehouse_inventory")
    op.drop_table("historical_complaints")
    op.drop_table("distribution_records")
    op.drop_table("deviations")
    op.drop_table("complaint_versions")
    op.drop_table("complaint_messages")
    op.drop_table("batch_equipment")
    op.drop_table("batch_packaging_material_lots")
    op.drop_table("batch_material_lots")
    op.drop_table("audit_events")
    op.drop_table("risk_assessment_versions")
    op.drop_table("packaging_material_lots")
    op.drop_table("material_lots")
    op.drop_table("equipment")
    op.drop_table("complaints")
    op.drop_table("complaint_attachments")
    op.drop_table("batches")
    op.drop_table("suppliers")
    op.drop_table("products")
    op.drop_table("manufacturing_lines")
    op.drop_table("complaint_drafts")
