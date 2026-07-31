from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.models.enums import ComplaintStatus, Priority, ProductType, SafetyRoute, Severity
from app.schemas.common import DecimalString, UTCDateTime

COMPLAINT_TEXT_FIELDS = (
    "thread_id",
    "complaint_source",
    "customer_name",
    "customer_contact",
    "country_market",
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
    "risk_rationale",
    "potential_hazard",
    "suggested_next_action",
    "created_by",
)

COMPLAINT_PATCH_TEXT_FIELDS = (
    "complaint_source",
    "customer_name",
    "customer_contact",
    "country_market",
    "product_name",
    "product_strength_grade",
    "dosage_form",
    "batch_lot_number",
    "quantity_unit",
    "complaint_type",
    "detailed_description",
    "storage_conditions",
    "risk_rationale",
    "potential_hazard",
    "suggested_next_action",
)


class ComplaintDraftCreate(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100)
    status: ComplaintStatus = ComplaintStatus.DRAFT
    complaint_source: str | None = Field(default=None, max_length=150)
    customer_name: str | None = Field(default=None, max_length=255)
    customer_contact: str | None = Field(default=None, max_length=255)
    country_market: str | None = Field(default=None, max_length=150)
    product_type: ProductType | None = None
    product_name: str | None = Field(default=None, max_length=255)
    product_strength_grade: str | None = Field(default=None, max_length=150)
    dosage_form: str | None = Field(default=None, max_length=100)
    batch_lot_number: str | None = Field(default=None, max_length=150)
    manufacturing_date: date | None = None
    manufacturing_date_text: str | None = Field(default=None, max_length=100)
    expiry_retest_date: date | None = None
    expiry_retest_date_text: str | None = Field(default=None, max_length=100)
    quantity_affected: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    quantity_unit: str | None = Field(default=None, max_length=50)
    complaint_type: str | None = Field(default=None, max_length=150)
    complaint_date: date | None = None
    detailed_description: str | None = None
    defect_observed_date: date | None = None
    sample_available: bool | None = None
    patient_consumed_product: bool | None = None
    adverse_event_signal: bool | None = None
    counterfeit_signal: bool | None = None
    storage_conditions: str | None = None
    suggested_severity: str | None = Field(default=None, max_length=30)
    suggested_priority: str | None = Field(default=None, max_length=30)
    safety_route: SafetyRoute | None = None
    risk_rationale: str | None = None
    potential_hazard: str | None = None
    suggested_next_action: str | None = None
    risk_confidence: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)
    missing_fields: dict[str, Any] | None = None
    created_by: str | None = Field(default=None, max_length=150)

    @field_validator(*COMPLAINT_TEXT_FIELDS, mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def validate_date_order(self) -> ComplaintDraftCreate:
        if (
            self.manufacturing_date
            and self.expiry_retest_date
            and self.expiry_retest_date < self.manufacturing_date
        ):
            raise ValueError("expiry_retest_date cannot be before manufacturing_date")
        return self


class ComplaintDraftCreateRequest(BaseModel):
    created_by: str | None = Field(default=None, max_length=150)

    @field_validator("created_by", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ComplaintDraftPatchFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint_source: str | None = Field(default=None, max_length=150)
    customer_name: str | None = Field(default=None, max_length=255)
    customer_contact: str | None = Field(default=None, max_length=255)
    country_market: str | None = Field(default=None, max_length=150)
    product_type: ProductType | None = None
    product_name: str | None = Field(default=None, max_length=255)
    product_strength_grade: str | None = Field(default=None, max_length=150)
    dosage_form: str | None = Field(default=None, max_length=100)
    batch_lot_number: str | None = Field(default=None, max_length=150)
    manufacturing_date: date | None = None
    manufacturing_date_text: str | None = Field(default=None, max_length=100)
    expiry_retest_date: date | None = None
    expiry_retest_date_text: str | None = Field(default=None, max_length=100)
    quantity_affected: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    quantity_unit: str | None = Field(default=None, max_length=50)
    complaint_type: str | None = Field(default=None, max_length=150)
    complaint_date: date | None = None
    detailed_description: str | None = None
    defect_observed_date: date | None = None
    sample_available: bool | None = None
    patient_consumed_product: bool | None = None
    adverse_event_signal: bool | None = None
    counterfeit_signal: bool | None = None
    storage_conditions: str | None = None
    suggested_severity: Severity | None = None
    suggested_priority: Priority | None = None
    safety_route: SafetyRoute | None = None
    risk_rationale: str | None = None
    potential_hazard: str | None = None
    suggested_next_action: str | None = None
    risk_confidence: Decimal | None = Field(default=None, ge=0, le=1, max_digits=5, decimal_places=4)
    missing_fields: dict[str, Any] | None = None

    @field_validator(*COMPLAINT_PATCH_TEXT_FIELDS, mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def validate_patch(self) -> ComplaintDraftPatchFields:
        if not self.model_fields_set:
            raise ValueError("patch must include at least one complaint field")
        if (
            self.manufacturing_date
            and self.expiry_retest_date
            and self.expiry_retest_date < self.manufacturing_date
        ):
            raise ValueError("expiry_retest_date cannot be before manufacturing_date")
        return self


class ComplaintDraftDevelopmentPatchRequest(BaseModel):
    patch: ComplaintDraftPatchFields
    actor_identifier: str | None = Field(default="Demo User", max_length=150)
    reason: str = Field(default="Development-only complaint draft population", max_length=500)
    source: str = Field(default="development-patch", max_length=100)

    @field_validator("actor_identifier", "reason", "source", mode="before")
    @classmethod
    def normalise_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ComplaintDraftStatusResponse(BaseModel):
    id: str
    status: str
    updated_at: UTCDateTime
    is_locked: bool
    is_committed: bool
    is_extraction_active: bool


class SaveComplaintRequest(BaseModel):
    reviewed_by: str = Field(min_length=1, max_length=150)
    review_meaning: str = Field(min_length=1, max_length=500)
    missing_information_acknowledged: bool = False
    change_reason: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=150)

    @field_validator("reviewed_by", "review_meaning", "change_reason", "idempotency_key", mode="before")
    @classmethod
    def normalise_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class ComplaintDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    thread_id: str
    status: str
    created_by: str | None = None
    complaint_source: str | None = None
    customer_name: str | None = None
    customer_contact: str | None = None
    country_market: str | None = None
    product_type: str | None = None
    product_name: str | None = None
    product_strength_grade: str | None = None
    dosage_form: str | None = None
    batch_lot_number: str | None = None
    manufacturing_date: date | None = None
    manufacturing_date_text: str | None = None
    expiry_retest_date: date | None = None
    expiry_retest_date_text: str | None = None
    quantity_affected: DecimalString | None = None
    quantity_unit: str | None = None
    complaint_type: str | None = None
    complaint_date: date | None = None
    detailed_description: str | None = None
    defect_observed_date: date | None = None
    sample_available: bool | None = None
    patient_consumed_product: bool | None = None
    adverse_event_signal: bool | None = None
    counterfeit_signal: bool | None = None
    storage_conditions: str | None = None
    suggested_severity: str | None = None
    suggested_priority: str | None = None
    safety_route: str | None = None
    risk_rationale: str | None = None
    potential_hazard: str | None = None
    suggested_next_action: str | None = None
    risk_confidence: DecimalString | None = None
    missing_fields: dict[str, Any] | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime

    @computed_field
    @property
    def is_locked(self) -> bool:
        return self.status in {
            ComplaintStatus.COMMITTED.value,
            ComplaintStatus.CLOSED.value,
            ComplaintStatus.CANCELLED.value,
        }

    @computed_field
    @property
    def is_committed(self) -> bool:
        return self.status == ComplaintStatus.COMMITTED.value

    @computed_field
    @property
    def is_extraction_active(self) -> bool:
        return False


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_number: str
    current_version_number: int
    status: str
    committed_from_draft_id: str | None = None
    committed_at: UTCDateTime
    committed_by: str
    review_meaning: str | None = None
    missing_information_acknowledged: bool
    unresolved_missing_information: dict[str, Any] | None = None
    latest_risk_assessment_id: str | None = None
    complaint_source: str | None = None
    customer_name: str | None = None
    customer_contact: str | None = None
    country_market: str | None = None
    product_type: str | None = None
    product_name: str | None = None
    product_strength_grade: str | None = None
    dosage_form: str | None = None
    batch_lot_number: str | None = None
    manufacturing_date: date | None = None
    manufacturing_date_text: str | None = None
    expiry_retest_date: date | None = None
    expiry_retest_date_text: str | None = None
    quantity_affected: DecimalString | None = None
    quantity_unit: str | None = None
    complaint_type: str | None = None
    complaint_date: date | None = None
    detailed_description: str | None = None
    defect_observed_date: date | None = None
    sample_available: bool | None = None
    patient_consumed_product: bool | None = None
    adverse_event_signal: bool | None = None
    counterfeit_signal: bool | None = None
    storage_conditions: str | None = None
    suggested_severity: str | None = None
    suggested_priority: str | None = None
    safety_route: str | None = None
    risk_rationale: str | None = None
    potential_hazard: str | None = None
    suggested_next_action: str | None = None
    risk_confidence: DecimalString | None = None
    missing_fields: dict[str, Any] | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class ComplaintLedgerListResponse(BaseModel):
    items: list[ComplaintResponse]
    limit: int
    offset: int
    next_offset: int | None = None


class ComplaintVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_id: str
    version_number: int
    snapshot: dict[str, Any]
    change_reason: str | None = None
    created_at: UTCDateTime
    created_by: str
    checksum: str


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str | None = None
    complaint_id: str | None = None
    event_type: str
    actor_type: str
    actor_identifier: str | None = None
    tool_name: str | None = None
    field_name: str | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    reason: str | None = None
    provider_name: str | None = None
    requested_model: str | None = None
    actual_model: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: UTCDateTime


class ComplaintAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    sha256_checksum: str
    extraction_status: str
    extraction_stage: str
    extraction_progress: int
    extraction_error: str | None = None
    created_at: UTCDateTime
    completed_at: UTCDateTime | None = None
    uploaded_by: str | None = None


class ComplaintAttachmentUploadResponse(BaseModel):
    attachment_id: str
    original_filename: str
    status: str
    progress_percentage: int
    current_stage: str
    duplicate: bool = False
    changed_fields: list[str] = Field(default_factory=list)
    created_at: UTCDateTime


class ComplaintAttachmentStatusResponse(BaseModel):
    attachment_id: str
    original_filename: str
    status: str
    progress_percentage: int
    current_stage: str
    safe_error: str | None = None
    created_at: UTCDateTime
    completed_at: UTCDateTime | None = None
