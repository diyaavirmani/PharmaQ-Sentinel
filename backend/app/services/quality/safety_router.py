from __future__ import annotations

from app.models.enums import SafetyRoute, Severity
from app.services.quality.schemas import (
    DefectCategory,
    DefectClassification,
    SafetyReviewRoute,
    SafetyRoutingResult,
)

SAFETY_ROUTER_VERSION = "safety-router-v1"


def route_safety(
    complaint: dict[str, object | None],
    classification: DefectClassification,
    severity_floor: Severity,
) -> SafetyRoutingResult:
    categories = set(classification.categories)
    routes: list[SafetyReviewRoute] = []
    reasons: dict[str, str] = {}

    def add(route: SafetyReviewRoute, reason: str) -> None:
        if route not in routes:
            routes.append(route)
            reasons[route.value] = reason

    quality_categories = categories - {DefectCategory.SERVICE_COMPLAINT, DefectCategory.UNKNOWN}
    if quality_categories:
        add(SafetyReviewRoute.QUALITY_ASSURANCE, "Product quality or manufacturing signal requires QA review.")
    if severity_floor != Severity.UNDETERMINED and DefectCategory.SERVICE_COMPLAINT not in categories:
        add(SafetyReviewRoute.QUALITY_ASSURANCE, "Configured safety rule matched a quality signal requiring QA review.")
    if complaint.get("adverse_event_signal") is True or categories & {
        DefectCategory.ADVERSE_REACTION,
        DefectCategory.LACK_OF_EFFECT,
    }:
        add(
            SafetyReviewRoute.PHARMACOVIGILANCE,
            "Possible adverse-event wording requires Pharmacovigilance review; no reportability decision is made.",
        )
    if categories & {DefectCategory.SUSPECTED_COUNTERFEIT_OR_TAMPERING}:
        add(SafetyReviewRoute.ANTI_COUNTERFEIT_REVIEW, "Counterfeit or tampering wording requires specialist review.")
        add(SafetyReviewRoute.REGULATORY_AFFAIRS_REVIEW, "Regulatory affairs should review potential regulatory implications.")
    if categories & {DefectCategory.STORAGE_OR_TRANSPORTATION, DefectCategory.CONTAINER_DAMAGE}:
        add(SafetyReviewRoute.SUPPLY_CHAIN_REVIEW, "Storage, transportation, or container handling context may be relevant.")
    if severity_floor == Severity.CRITICAL:
        add(SafetyReviewRoute.REGULATORY_AFFAIRS_REVIEW, "Critical safety floor requires regulatory affairs awareness.")
    if categories == {DefectCategory.SERVICE_COMPLAINT}:
        add(SafetyReviewRoute.CUSTOMER_SERVICE, "Issue appears service-only based on available information.")
    if not routes:
        add(SafetyReviewRoute.UNDETERMINED, "Insufficient information for a specific review route.")

    case_type = SafetyRoute.UNDETERMINED
    if SafetyReviewRoute.PHARMACOVIGILANCE in routes and SafetyReviewRoute.QUALITY_ASSURANCE in routes:
        case_type = SafetyRoute.QUALITY_AND_ADVERSE_EVENT
    elif SafetyReviewRoute.PHARMACOVIGILANCE in routes:
        case_type = SafetyRoute.POSSIBLE_ADVERSE_EVENT
    elif SafetyReviewRoute.ANTI_COUNTERFEIT_REVIEW in routes:
        case_type = SafetyRoute.COUNTERFEIT_OR_TAMPERING
    elif SafetyReviewRoute.SUPPLY_CHAIN_REVIEW in routes and SafetyReviewRoute.QUALITY_ASSURANCE not in routes:
        case_type = SafetyRoute.DISTRIBUTION_OR_STORAGE
    elif SafetyReviewRoute.CUSTOMER_SERVICE in routes and len(routes) == 1:
        case_type = SafetyRoute.SERVICE_ONLY
    elif SafetyReviewRoute.QUALITY_ASSURANCE in routes:
        case_type = SafetyRoute.PRODUCT_QUALITY

    return SafetyRoutingResult(routes=routes, case_type=case_type, route_reasons=reasons)
