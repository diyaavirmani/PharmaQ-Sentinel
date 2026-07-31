from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import Enum

from app.models.enums import Priority, Severity
from app.services.llm import BaseLLMGateway, LLMGatewayError, LLMRequestContext
from app.services.quality.completeness import evaluate_completeness
from app.services.quality.defect_taxonomy import classify_defects
from app.services.quality.safety_router import route_safety
from app.services.quality.safety_rules import (
    SEVERITY_RANK,
    evaluate_safety_rules,
    priority_for_severity,
)
from app.services.quality.schemas import HybridRiskAssessment, PharmaRiskAssessment

PHARMA_RISK_PROMPT_VERSION = "pharma-risk-assessment-v1"
PHARMA_RISK_PROMPT = """
You are PharmaQ Sentinel's pharmaceutical complaint risk assistant.

Return only the requested structured assessment. Treat all outputs as draft suggestions requiring authorised QA review.
Do not make product-release, recall, reportability, regulatory notification, diagnosis, root-cause, or CAPA decisions.
Use the deterministic severity floor as the minimum severity. You may increase severity, but you may not downgrade below it.
Include evidence, confidence, limitations, and safe follow-up actions.
If possible adverse-event wording appears, say it should be routed for Pharmacovigilance review and more information should be collected.
Never state that a case is legally reportable.
"""


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _serialisable_complaint(complaint: dict[str, object | None]) -> dict[str, object | None]:
    return json.loads(json.dumps(complaint, default=_json_default, sort_keys=True))


def _join_items(items: list[str], fallback: str) -> str:
    cleaned = [item for item in items if item]
    return "; ".join(cleaned) if cleaned else fallback


def _fallback_assessment(
    complaint: dict[str, object | None],
    *,
    minimum: Severity,
    priority: Priority,
    quality_defect_possible: bool,
    adverse_event_possible: bool,
    counterfeit_possible: bool,
    distribution_issue_possible: bool,
    supporting_evidence: list[str],
    missing_information: list[str],
    limitations: list[str],
) -> PharmaRiskAssessment:
    product = complaint.get("product_name") or "the reported product"
    batch = complaint.get("batch_lot_number") or "the reported batch when available"
    rationale = (
        f"Draft triage is based on the available complaint information for {product} and {batch}. "
        "The deterministic safety floor and configured routing rules were applied; authorised QA review is required."
    )
    return PharmaRiskAssessment(
        suggested_severity=minimum,
        suggested_priority=priority,
        patient_harm_level=None,
        quality_defect_possible=quality_defect_possible,
        adverse_event_possible=adverse_event_possible,
        counterfeit_possible=counterfeit_possible,
        distribution_issue_possible=distribution_issue_possible,
        rationale=rationale,
        potential_hazards=["Potential quality impact cannot be excluded from available information."]
        if quality_defect_possible
        else ["No product-quality hazard can be confirmed from available information."],
        supporting_evidence=supporting_evidence,
        contradicting_evidence=[],
        recommended_actions=[
            "QA should review the complaint, source evidence, and missing information before any authorised decision.",
        ],
        missing_information=missing_information[:8],
        confidence=0.62 if minimum != Severity.UNDETERMINED else 0.35,
        limitations=limitations,
        requires_qa_confirmation=True,
    )


def _coerce_contextual_assessment(raw: object) -> PharmaRiskAssessment:
    if isinstance(raw, PharmaRiskAssessment):
        return raw
    suggested_severity = getattr(raw, "suggested_severity", Severity.UNDETERMINED)
    if isinstance(suggested_severity, str):
        suggested_severity = Severity(suggested_severity)
    suggested_priority = getattr(raw, "suggested_priority", priority_for_severity(suggested_severity))
    if isinstance(suggested_priority, str):
        suggested_priority = Priority(suggested_priority)
    risk_rationale = getattr(raw, "risk_rationale", None) or getattr(raw, "rationale", None) or (
        "Draft risk assessment requires authorised QA review."
    )
    potential_hazard = getattr(raw, "potential_hazard", None)
    recommended_next_action = getattr(raw, "recommended_next_action", None) or getattr(raw, "suggested_next_action", None)
    supporting_fields = getattr(raw, "supporting_fields", [])
    return PharmaRiskAssessment(
        suggested_severity=suggested_severity,
        suggested_priority=suggested_priority,
        patient_harm_level=getattr(raw, "patient_harm_level", None),
        quality_defect_possible=True,
        adverse_event_possible=False,
        counterfeit_possible=False,
        distribution_issue_possible=False,
        rationale=risk_rationale,
        potential_hazards=[potential_hazard] if potential_hazard else [],
        supporting_evidence=[str(item) for item in supporting_fields],
        contradicting_evidence=[],
        recommended_actions=[recommended_next_action] if recommended_next_action else [],
        missing_information=[],
        confidence=getattr(raw, "confidence", 0.5),
        limitations=list(getattr(raw, "limitations", [])),
        requires_qa_confirmation=True,
    )


def _apply_deterministic_floor(
    assessment: PharmaRiskAssessment,
    *,
    minimum: Severity,
    warnings: list[str],
) -> PharmaRiskAssessment:
    if SEVERITY_RANK[assessment.suggested_severity] >= SEVERITY_RANK[minimum]:
        return assessment
    warnings.append(
        f"Contextual assessment suggested {assessment.suggested_severity.value}, "
        f"but deterministic safety floor requires {minimum.value}; human review required."
    )
    return assessment.model_copy(
        update={
            "suggested_severity": minimum,
            "suggested_priority": priority_for_severity(minimum),
            "limitations": [
                *assessment.limitations,
                "Severity was raised to the deterministic safety floor; authorised QA review is required.",
            ],
        }
    )


def _material_fingerprint(payload: dict[str, object]) -> str:
    serialised = json.dumps(payload, default=_json_default, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def assess_pharma_risk(
    *,
    complaint: dict[str, object | None],
    latest_user_message: str,
    changed_fields: list[str],
    request_id: str,
    draft_id: str,
    thread_id: str,
    llm_gateway: BaseLLMGateway,
) -> HybridRiskAssessment:
    completeness = evaluate_completeness(complaint)
    classification = classify_defects(complaint)
    deterministic = evaluate_safety_rules(complaint, classification)
    routing = route_safety(complaint, classification, deterministic.severity_floor)
    warnings = [*completeness.warnings, *deterministic.warnings, *routing.warnings]
    quality_defect_possible = any(route.value == "QUALITY_ASSURANCE" for route in routing.routes)
    adverse_event_possible = any(route.value == "PHARMACOVIGILANCE" for route in routing.routes)
    counterfeit_possible = any(route.value == "ANTI_COUNTERFEIT_REVIEW" for route in routing.routes)
    distribution_issue_possible = any(route.value == "SUPPLY_CHAIN_REVIEW" for route in routing.routes)
    supporting = [
        f"{match.signal}: {match.evidence}"
        for match in deterministic.matches
    ] or [
        field
        for field in ("product_name", "batch_lot_number", "complaint_type", "detailed_description")
        if complaint.get(field)
    ]
    limitations = [
        "AI-assisted triage is a draft recommendation and is not an authorised QA decision.",
        "No product-release, recall, reportability, diagnosis, root-cause, or CAPA conclusion is made.",
    ]

    try:
        result = llm_gateway.generate_structured(
            system_instructions=PHARMA_RISK_PROMPT,
            user_input=json.dumps(
                {
                    "draft": _serialisable_complaint(complaint),
                    "deterministic_severity_floor": deterministic.severity_floor.value,
                    "deterministic_rule_matches": [match.model_dump(mode="json") for match in deterministic.matches],
                    "defect_categories": [category.value for category in classification.categories],
                    "safety_routes": [route.value for route in routing.routes],
                    "case_type": routing.case_type.value,
                    "completeness": completeness.model_dump(mode="json"),
                    "latest_user_message": latest_user_message,
                },
                default=_json_default,
                sort_keys=True,
            ),
            response_schema=PharmaRiskAssessment,
            request_context=LLMRequestContext(
                request_id=request_id,
                draft_id=draft_id,
                thread_id=thread_id,
                tool_name="PHARMA_RISK_ASSESSMENT",
                purpose="Generate draft pharmaceutical complaint risk classification and safety routing context",
                prompt_version=PHARMA_RISK_PROMPT_VERSION,
                contains_sensitive_information=True,
                metadata={
                    "changed_field_count": len(changed_fields),
                    "changed_fields": ",".join(changed_fields[:20]),
                    "rule_version": deterministic.rule_version,
                },
            ),
            temperature=0,
            max_output_tokens=1800,
        )
        assessment = _coerce_contextual_assessment(result.parsed_output)
        provider_name = result.provider
        requested_model = result.requested_model
        actual_model = result.actual_model
        prompt_version = PHARMA_RISK_PROMPT_VERSION
        warnings.extend(result.warnings)
    except LLMGatewayError as exc:
        assessment = _fallback_assessment(
            complaint,
            minimum=deterministic.severity_floor,
            priority=deterministic.priority_floor,
            quality_defect_possible=quality_defect_possible,
            adverse_event_possible=adverse_event_possible,
            counterfeit_possible=counterfeit_possible,
            distribution_issue_possible=distribution_issue_possible,
            supporting_evidence=supporting,
            missing_information=[*completeness.missing_critical_fields, *completeness.missing_recommended_fields],
            limitations=limitations,
        )
        provider_name = None
        requested_model = None
        actual_model = None
        prompt_version = PHARMA_RISK_PROMPT_VERSION
        warnings.append(f"OpenAI risk assessment unavailable; used deterministic safety engine ({exc.__class__.__name__}).")

    assessment = _apply_deterministic_floor(
        assessment,
        minimum=deterministic.severity_floor,
        warnings=warnings,
    )
    if not assessment.supporting_evidence:
        assessment = assessment.model_copy(update={"supporting_evidence": supporting})
    material = {
        "severity": assessment.suggested_severity.value,
        "priority": assessment.suggested_priority.value,
        "routes": [route.value for route in routing.routes],
        "case_type": routing.case_type.value,
        "rule_matches": [match.rule_id for match in deterministic.matches],
        "supporting_evidence": assessment.supporting_evidence,
        "contradicting_evidence": assessment.contradicting_evidence,
    }
    return HybridRiskAssessment(
        assessment=assessment,
        completeness=completeness,
        defect_classification=classification,
        deterministic=deterministic,
        routing=routing,
        provider_name=provider_name,
        requested_model=requested_model,
        actual_model=actual_model,
        prompt_version=prompt_version,
        warnings=warnings,
        material_fingerprint=_material_fingerprint(material),
    )


def draft_risk_patch(result: HybridRiskAssessment) -> dict[str, object]:
    assessment = result.assessment
    return {
        "suggested_severity": assessment.suggested_severity.value,
        "suggested_priority": assessment.suggested_priority.value,
        "safety_route": result.routing.case_type.value,
        "risk_rationale": assessment.rationale,
        "potential_hazard": _join_items(
            assessment.potential_hazards,
            "Potential hazards could not be determined from available information.",
        ),
        "suggested_next_action": _join_items(
            assessment.recommended_actions,
            "QA should review the complaint and request missing information.",
        ),
        "risk_confidence": Decimal(str(assessment.confidence)),
        "missing_fields": {
            "critical": result.completeness.missing_critical_fields,
            "recommended": result.completeness.missing_recommended_fields,
            "questions": result.completeness.targeted_follow_up_questions,
            "completeness": result.completeness.model_dump(mode="json"),
            "risk": {
                "route_chips": [route.value for route in result.routing.routes],
                "case_type": result.routing.case_type.value,
                "confidence": assessment.confidence,
                "one_line_rationale": assessment.rationale,
                "potential_hazards": assessment.potential_hazards,
                "supporting_evidence": assessment.supporting_evidence,
                "contradicting_evidence": assessment.contradicting_evidence,
                "recommended_actions": assessment.recommended_actions,
                "limitations": assessment.limitations,
                "requires_qa_confirmation": assessment.requires_qa_confirmation,
                "deterministic_severity_floor": result.deterministic.severity_floor.value,
                "critical_signals": [
                    match.signal
                    for match in result.deterministic.matches
                    if match.severity_floor == Severity.CRITICAL
                ],
            },
        },
    }
