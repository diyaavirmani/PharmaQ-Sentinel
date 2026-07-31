from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Priority, SafetyRoute, Severity


class SafetyReviewRoute(str, Enum):
    QUALITY_ASSURANCE = "QUALITY_ASSURANCE"
    PHARMACOVIGILANCE = "PHARMACOVIGILANCE"
    REGULATORY_AFFAIRS_REVIEW = "REGULATORY_AFFAIRS_REVIEW"
    SUPPLY_CHAIN_REVIEW = "SUPPLY_CHAIN_REVIEW"
    ANTI_COUNTERFEIT_REVIEW = "ANTI_COUNTERFEIT_REVIEW"
    CUSTOMER_SERVICE = "CUSTOMER_SERVICE"
    UNDETERMINED = "UNDETERMINED"


class DefectCategory(str, Enum):
    PRODUCT_APPEARANCE = "PRODUCT_APPEARANCE"
    PACKAGING_LEAKAGE = "PACKAGING_LEAKAGE"
    BROKEN_OR_DAMAGED_DOSAGE_FORM = "BROKEN_OR_DAMAGED_DOSAGE_FORM"
    INCORRECT_LABEL = "INCORRECT_LABEL"
    WRONG_PRODUCT = "WRONG_PRODUCT"
    WRONG_STRENGTH = "WRONG_STRENGTH"
    MISSING_QUANTITY = "MISSING_QUANTITY"
    FOREIGN_MATTER = "FOREIGN_MATTER"
    CONTAMINATION = "CONTAMINATION"
    STERILITY_CONCERN = "STERILITY_CONCERN"
    API_ASSAY_DISCREPANCY = "API_ASSAY_DISCREPANCY"
    API_IMPURITY_DISCREPANCY = "API_IMPURITY_DISCREPANCY"
    API_MOISTURE_DISCREPANCY = "API_MOISTURE_DISCREPANCY"
    CONTAINER_DAMAGE = "CONTAINER_DAMAGE"
    STORAGE_OR_TRANSPORTATION = "STORAGE_OR_TRANSPORTATION"
    LACK_OF_EFFECT = "LACK_OF_EFFECT"
    ADVERSE_REACTION = "ADVERSE_REACTION"
    SUSPECTED_COUNTERFEIT_OR_TAMPERING = "SUSPECTED_COUNTERFEIT_OR_TAMPERING"
    SERVICE_COMPLAINT = "SERVICE_COMPLAINT"
    UNKNOWN = "UNKNOWN"


class CompletenessResult(BaseModel):
    completeness_percentage: int = Field(ge=0, le=100)
    can_begin_triage: bool
    missing_critical_fields: list[str] = Field(default_factory=list)
    missing_recommended_fields: list[str] = Field(default_factory=list)
    targeted_follow_up_questions: list[str] = Field(default_factory=list, max_length=3)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DefectClassification(BaseModel):
    categories: list[DefectCategory]
    evidence_terms: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class SafetyRuleMatch(BaseModel):
    rule_id: str
    severity_floor: Severity
    signal: str
    evidence: str


class DeterministicSafetyResult(BaseModel):
    rule_version: str
    severity_floor: Severity
    priority_floor: Priority
    matches: list[SafetyRuleMatch] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SafetyRoutingResult(BaseModel):
    routes: list[SafetyReviewRoute]
    case_type: SafetyRoute
    route_reasons: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class PharmaRiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggested_severity: Severity
    suggested_priority: Priority
    patient_harm_level: str | None = Field(default=None, max_length=60)
    quality_defect_possible: bool = False
    adverse_event_possible: bool = False
    counterfeit_possible: bool = False
    distribution_issue_possible: bool = False
    rationale: str = Field(min_length=1, max_length=1800)
    potential_hazards: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)
    requires_qa_confirmation: Literal[True] = True

    @field_validator(
        "potential_hazards",
        "supporting_evidence",
        "contradicting_evidence",
        "recommended_actions",
        "missing_information",
        "limitations",
    )
    @classmethod
    def trim_text_items(cls, value: list[str]) -> list[str]:
        return [" ".join(item.strip().split()) for item in value if item.strip()]


class HybridRiskAssessment(BaseModel):
    assessment: PharmaRiskAssessment
    completeness: CompletenessResult
    defect_classification: DefectClassification
    deterministic: DeterministicSafetyResult
    routing: SafetyRoutingResult
    provider_name: str | None = None
    requested_model: str | None = None
    actual_model: str | None = None
    prompt_version: str
    warnings: list[str] = Field(default_factory=list)
    material_fingerprint: str
