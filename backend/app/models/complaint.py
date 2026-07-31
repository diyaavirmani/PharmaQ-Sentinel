from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import CHAR, DATETIME, JSON, LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import (
    MYSQL_TABLE_KWARGS,
    Base,
    CreatedByMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    normalise_optional_string,
    utc_now,
)
from app.models.enums import (
    ActorType,
    ComplaintStatus,
    ExtractionStatus,
    MessageRole,
    Priority,
    SafetyRoute,
    Severity,
)

OPTIONAL_STRING_FIELDS = {
    "thread_id",
    "complaint_source",
    "customer_name",
    "customer_contact",
    "country_market",
    "product_type",
    "product_name",
    "product_strength_grade",
    "dosage_form",
    "batch_lot_number",
    "manufacturing_date_text",
    "expiry_retest_date_text",
    "quantity_unit",
    "complaint_type",
    "detailed_description",
    "storage_conditions",
    "suggested_severity",
    "suggested_priority",
    "safety_route",
    "risk_rationale",
    "potential_hazard",
    "suggested_next_action",
    "created_by",
}


class ComplaintFieldMixin:
    complaint_source: Mapped[str | None] = mapped_column(String(150), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_market: Mapped[str | None] = mapped_column(String(150), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_strength_grade: Mapped[str | None] = mapped_column(String(150), nullable=True)
    dosage_form: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_lot_number: Mapped[str | None] = mapped_column(String(150), nullable=True)
    manufacturing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    manufacturing_date_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expiry_retest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_retest_date_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity_affected: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    complaint_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    complaint_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    detailed_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    defect_observed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sample_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    patient_consumed_product: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    adverse_event_signal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    counterfeit_signal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    storage_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_severity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    suggested_priority: Mapped[str | None] = mapped_column(String(30), nullable=True)
    safety_route: Mapped[str | None] = mapped_column(String(50), nullable=True)
    risk_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    potential_hazard: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    missing_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ComplaintDraft(UUIDPrimaryKeyMixin, TimestampMixin, CreatedByMixin, ComplaintFieldMixin, Base):
    __tablename__ = "complaint_drafts"
    __table_args__ = (
        UniqueConstraint("thread_id", name="uq_complaint_drafts_thread_id"),
        CheckConstraint("quantity_affected IS NULL OR quantity_affected >= 0", name="quantity_affected_non_negative"),
        CheckConstraint("risk_confidence IS NULL OR (risk_confidence >= 0 AND risk_confidence <= 1)", name="risk_confidence_between_zero_and_one"),
        Index("ix_complaint_drafts_thread_id", "thread_id"),
        Index("ix_complaint_drafts_status", "status"),
        Index("ix_complaint_drafts_batch_lot_number", "batch_lot_number"),
        Index("ix_complaint_drafts_complaint_type", "complaint_type"),
        Index("ix_complaint_drafts_suggested_severity", "suggested_severity"),
        Index("ix_complaint_drafts_created_at", "created_at"),
        MYSQL_TABLE_KWARGS,
    )

    thread_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=ComplaintStatus.DRAFT.value, nullable=False)

    messages: Mapped[list[ComplaintMessage]] = relationship(back_populates="draft")
    attachments: Mapped[list[ComplaintAttachment]] = relationship(back_populates="draft")
    field_evidence: Mapped[list[FieldEvidence]] = relationship(back_populates="draft")
    risk_assessments: Mapped[list[RiskAssessmentVersion]] = relationship(back_populates="draft")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="draft")
    agent_runs: Mapped[list[AgentRun]] = relationship(back_populates="draft")
    batch_impact_runs: Mapped[list[BatchImpactRun]] = relationship(back_populates="draft")
    quality_war_room_runs: Mapped[list[QualityWarRoomRun]] = relationship(back_populates="draft")
    duplicate_analysis_runs: Mapped[list[DuplicateAnalysisRun]] = relationship(back_populates="draft")
    investigation_playbook_runs: Mapped[list[InvestigationPlaybookRun]] = relationship(back_populates="draft")
    investigation_review_actions: Mapped[list[InvestigationReviewAction]] = relationship(back_populates="draft")
    committed_complaints: Mapped[list[Complaint]] = relationship(back_populates="committed_from_draft")

    @validates(*OPTIONAL_STRING_FIELDS)
    def _normalise_strings(self, key: str, value: str | None) -> str | None:
        normalised = normalise_optional_string(value)
        if key == "thread_id" and normalised is not None and len(normalised) > 100:
            raise ValueError("thread_id must not exceed 100 characters")
        return normalised

    @validates("quantity_affected")
    def _validate_quantity(self, _key: str, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("quantity_affected cannot be negative")
        return value

    @validates("risk_confidence")
    def _validate_confidence(self, _key: str, value: Decimal | None) -> Decimal | None:
        if value is not None and not Decimal(0) <= value <= Decimal(1):
            raise ValueError("risk_confidence must be between zero and one")
        return value

    @validates("manufacturing_date", "expiry_retest_date")
    def _validate_date_order(self, key: str, value: date | None) -> date | None:
        manufacturing_date = value if key == "manufacturing_date" else self.manufacturing_date
        expiry_retest_date = value if key == "expiry_retest_date" else self.expiry_retest_date
        if (
            manufacturing_date is not None
            and expiry_retest_date is not None
            and expiry_retest_date < manufacturing_date
        ):
            raise ValueError("expiry_retest_date cannot be before manufacturing_date")
        return value


class Complaint(UUIDPrimaryKeyMixin, TimestampMixin, ComplaintFieldMixin, Base):
    __tablename__ = "complaints"
    __table_args__ = (
        UniqueConstraint("complaint_number", name="uq_complaints_complaint_number"),
        UniqueConstraint("save_idempotency_key", name="uq_complaints_save_idempotency_key"),
        CheckConstraint("current_version_number > 0", name="current_version_number_positive"),
        CheckConstraint("quantity_affected IS NULL OR quantity_affected >= 0", name="quantity_affected_non_negative"),
        CheckConstraint("risk_confidence IS NULL OR (risk_confidence >= 0 AND risk_confidence <= 1)", name="risk_confidence_between_zero_and_one"),
        Index("ix_complaints_complaint_number", "complaint_number"),
        Index("ix_complaints_save_idempotency_key", "save_idempotency_key"),
        Index("ix_complaints_status", "status"),
        Index("ix_complaints_batch_lot_number", "batch_lot_number"),
        Index("ix_complaints_product_name", "product_name"),
        Index("ix_complaints_customer_name", "customer_name"),
        Index("ix_complaints_complaint_type", "complaint_type"),
        Index("ix_complaints_suggested_severity", "suggested_severity"),
        Index("ix_complaints_complaint_date", "complaint_date"),
        Index("ix_complaints_committed_at", "committed_at"),
        MYSQL_TABLE_KWARGS,
    )

    complaint_number: Mapped[str] = mapped_column(String(40), nullable=False)
    current_version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default=ComplaintStatus.COMMITTED.value, nullable=False)
    save_idempotency_key: Mapped[str | None] = mapped_column(String(150), nullable=True)
    review_meaning: Mapped[str | None] = mapped_column(String(500), nullable=True)
    missing_information_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unresolved_missing_information: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latest_risk_assessment_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("risk_assessment_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    committed_from_draft_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    committed_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)
    committed_by: Mapped[str] = mapped_column(String(150), nullable=False)

    committed_from_draft: Mapped[ComplaintDraft | None] = relationship(back_populates="committed_complaints")
    latest_risk_assessment: Mapped[RiskAssessmentVersion | None] = relationship()
    versions: Mapped[list[ComplaintVersion]] = relationship(back_populates="complaint")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="complaint")

    @validates("quantity_affected")
    def _validate_quantity(self, _key: str, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("quantity_affected cannot be negative")
        return value

    @validates("risk_confidence")
    def _validate_confidence(self, _key: str, value: Decimal | None) -> Decimal | None:
        if value is not None and not Decimal(0) <= value <= Decimal(1):
            raise ValueError("risk_confidence must be between zero and one")
        return value

    @validates("manufacturing_date", "expiry_retest_date")
    def _validate_date_order(self, key: str, value: date | None) -> date | None:
        manufacturing_date = value if key == "manufacturing_date" else self.manufacturing_date
        expiry_retest_date = value if key == "expiry_retest_date" else self.expiry_retest_date
        if (
            manufacturing_date is not None
            and expiry_retest_date is not None
            and expiry_retest_date < manufacturing_date
        ):
            raise ValueError("expiry_retest_date cannot be before manufacturing_date")
        return value


class ComplaintNumberSequence(Base):
    __tablename__ = "complaint_number_sequences"
    __table_args__ = (
        CheckConstraint("next_number > 0", name="next_number_positive"),
        MYSQL_TABLE_KWARGS,
    )

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_number: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)


class ComplaintVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "complaint_versions"
    __table_args__ = (
        UniqueConstraint("complaint_id", "version_number", name="uq_complaint_versions_complaint_id_version_number"),
        CheckConstraint("version_number > 0", name="version_number_positive"),
        CheckConstraint("CHAR_LENGTH(checksum) = 64", name="checksum_sha256_hex_length"),
        Index("ix_complaint_versions_complaint_id", "complaint_id"),
        MYSQL_TABLE_KWARGS,
    )

    complaint_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(150), nullable=False)
    checksum: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    complaint: Mapped[Complaint] = relationship(back_populates="versions")


class ComplaintMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "complaint_messages"
    __table_args__ = (
        Index("ix_complaint_messages_draft_id", "draft_id"),
        Index("ix_complaint_messages_created_at", "created_at"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(30), default=MessageRole.USER.value, nullable=False)
    message_text: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    attachment_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_attachments.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="messages")
    attachment: Mapped[ComplaintAttachment | None] = relationship(back_populates="messages")
    field_evidence: Mapped[list[FieldEvidence]] = relationship(back_populates="source_message")


class ComplaintAttachment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "complaint_attachments"
    __table_args__ = (
        CheckConstraint("file_size >= 0", name="file_size_non_negative"),
        Index("ix_complaint_attachments_draft_id", "draft_id"),
        Index("ix_complaint_attachments_sha256_checksum", "sha256_checksum"),
        Index("ix_complaint_attachments_extraction_status", "extraction_status"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    extraction_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_status: Mapped[str] = mapped_column(
        String(40),
        default=ExtractionStatus.PENDING.value,
        nullable=False,
    )
    extraction_stage: Mapped[str] = mapped_column(String(40), default="UPLOADING", nullable=False)
    extraction_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(150), nullable=True)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="attachments")
    messages: Mapped[list[ComplaintMessage]] = relationship(back_populates="attachment")
    field_evidence: Mapped[list[FieldEvidence]] = relationship(back_populates="source_attachment")


class FieldEvidence(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "field_evidence"
    __table_args__ = (
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_between_zero_and_one"),
        Index("ix_field_evidence_draft_id", "draft_id"),
        Index("ix_field_evidence_field_name", "field_name"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(150), nullable=False)
    field_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_attachment_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_attachments.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_message_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paragraph_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_explicit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="field_evidence")
    source_attachment: Mapped[ComplaintAttachment | None] = relationship(back_populates="field_evidence")
    source_message: Mapped[ComplaintMessage | None] = relationship(back_populates="field_evidence")


class RiskAssessmentVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "risk_assessment_versions"
    __table_args__ = (
        UniqueConstraint("draft_id", "version_number", name="uq_risk_assessment_versions_draft_id_version_number"),
        CheckConstraint("version_number > 0", name="version_number_positive"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_between_zero_and_one"),
        Index("ix_risk_assessment_versions_draft_id", "draft_id"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), default=Severity.UNDETERMINED.value, nullable=False)
    priority: Mapped[str] = mapped_column(String(30), default=Priority.UNDETERMINED.value, nullable=False)
    patient_harm_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    safety_route: Mapped[str | None] = mapped_column(String(50), default=SafetyRoute.UNDETERMINED.value, nullable=True)
    risk_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    potential_hazard: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    supporting_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contradicting_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    requested_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    actual_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="risk_assessments")


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_draft_id", "draft_id"),
        Index("ix_audit_events_complaint_id", "complaint_id"),
        Index("ix_audit_events_event_type", "event_type"),
        Index("ix_audit_events_created_at", "created_at"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    complaint_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("complaints.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(30), default=ActorType.SYSTEM.value, nullable=False)
    actor_identifier: Mapped[str | None] = mapped_column(String(150), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    field_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    requested_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    actual_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)

    draft: Mapped[ComplaintDraft | None] = relationship(back_populates="audit_events")
    complaint: Mapped[Complaint | None] = relationship(back_populates="audit_events")


class AgentRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_draft_id", "draft_id"),
        Index("ix_agent_runs_request_id", "request_id"),
        Index("ix_agent_runs_intent", "intent"),
        Index("ix_agent_runs_status", "status"),
        Index("ix_agent_runs_started_at", "started_at"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(String(150), nullable=False)
    intent: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    requested_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    actual_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    errors_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="agent_runs")


class BatchImpactRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "batch_impact_runs"
    __table_args__ = (
        Index("ix_batch_impact_runs_draft_id", "draft_id"),
        Index("ix_batch_impact_runs_status", "status"),
        Index("ix_batch_impact_runs_created_at", "created_at"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    graph_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    signals_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    limitations_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(150), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="batch_impact_runs")


class QualityWarRoomRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quality_war_room_runs"
    __table_args__ = (
        Index("ix_quality_war_room_runs_draft_id", "draft_id"),
        Index("ix_quality_war_room_runs_status", "status"),
        Index("ix_quality_war_room_runs_started_at", "started_at"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    iteration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    specialist_outputs_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    auditor_output_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    consensus_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="quality_war_room_runs")
    events: Mapped[list[QualityWarRoomEvent]] = relationship(back_populates="run")


class QualityWarRoomEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quality_war_room_events"
    __table_args__ = (
        Index("ix_quality_war_room_events_run_id", "run_id"),
        Index("ix_quality_war_room_events_event_type", "event_type"),
        Index("ix_quality_war_room_events_created_at", "created_at"),
        MYSQL_TABLE_KWARGS,
    )

    run_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("quality_war_room_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    concise_message: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence_ids_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)

    run: Mapped[QualityWarRoomRun] = relationship(back_populates="events")


class DuplicateAnalysisRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "duplicate_analysis_runs"
    __table_args__ = (
        Index("ix_duplicate_analysis_runs_draft_id", "draft_id"),
        Index("ix_duplicate_analysis_runs_status", "status"),
        Index("ix_duplicate_analysis_runs_created_at", "created_at"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(150), nullable=True)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="duplicate_analysis_runs")


class InvestigationPlaybookRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "investigation_playbook_runs"
    __table_args__ = (
        Index("ix_investigation_playbook_runs_draft_id", "draft_id"),
        Index("ix_investigation_playbook_runs_status", "status"),
        Index("ix_investigation_playbook_runs_created_at", "created_at"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    playbook_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(150), nullable=True)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="investigation_playbook_runs")


class InvestigationReviewAction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "investigation_review_actions"
    __table_args__ = (
        Index("ix_investigation_review_actions_draft_id", "draft_id"),
        Index("ix_investigation_review_actions_run_id", "run_id"),
        Index("ix_investigation_review_actions_created_at", "created_at"),
        MYSQL_TABLE_KWARGS,
    )

    draft_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("complaint_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    original_text_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    saved_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor_identifier: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now, nullable=False)

    draft: Mapped[ComplaintDraft] = relationship(back_populates="investigation_review_actions")
