from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import Priority, Severity
from app.services.quality.defect_taxonomy import DefectCategory
from app.services.quality.schemas import (
    DefectClassification,
    DeterministicSafetyResult,
    SafetyRuleMatch,
)

SAFETY_RULE_VERSION = "safety-rules-v1"
SEVERITY_RANK = {
    Severity.UNDETERMINED: 0,
    Severity.MINOR: 1,
    Severity.MAJOR: 2,
    Severity.CRITICAL: 3,
}


@dataclass(frozen=True)
class SafetyRule:
    rule_id: str
    severity_floor: Severity
    signal: str
    terms: tuple[str, ...]
    categories: tuple[DefectCategory, ...] = ()


SAFETY_RULES: tuple[SafetyRule, ...] = (
    SafetyRule("critical-death", Severity.CRITICAL, "death", ("death",)),
    SafetyRule("critical-life-threatening", Severity.CRITICAL, "life-threatening event", ("life-threatening",)),
    SafetyRule("critical-hospitalisation", Severity.CRITICAL, "hospitalisation", ("hospitalisation", "hospitalization", "hospital treatment")),
    SafetyRule("critical-wrong-product", Severity.CRITICAL, "wrong product", ("wrong product", "product mix-up")),
    SafetyRule("critical-wrong-strength", Severity.CRITICAL, "wrong strength", ("wrong strength", "incorrect strength")),
    SafetyRule("critical-sterility", Severity.CRITICAL, "sterility failure", ("sterility failure", "sterile failure", "non-sterile")),
    SafetyRule("critical-contamination", Severity.CRITICAL, "confirmed contamination", ("confirmed contamination", "microbial contamination")),
    SafetyRule("critical-dangerous-foreign-matter", Severity.CRITICAL, "dangerous foreign matter", ("glass particle", "metal particle")),
    SafetyRule("critical-counterfeit", Severity.CRITICAL, "counterfeit or tampering", ("counterfeit", "tamper", "tampering")),
    SafetyRule("critical-multiple-serious", Severity.CRITICAL, "multiple serious cases", ("multiple serious", "widespread affected batches")),
    SafetyRule("major-discolouration", Severity.MAJOR, "possible degradation from discolouration", ("discolouration", "discoloration", "discoloured", "discolored")),
    SafetyRule("major-blister-leakage", Severity.MAJOR, "blister leakage or compromised seal", ("blister leakage", "compromised seal", "seal leak", "leaking blister")),
    SafetyRule("major-api-assay", Severity.MAJOR, "API assay failure", ("api assay failure", "assay failure", "assay discrepancy")),
    SafetyRule("major-moisture", Severity.MAJOR, "significant moisture discrepancy", ("moisture discrepancy", "high moisture")),
    SafetyRule("major-label-error", Severity.MAJOR, "label information error", ("wrong label", "incorrect label")),
    SafetyRule("major-repeated-complaints", Severity.MAJOR, "repeated related complaints", ("repeated related complaints", "multiple related batches")),
    SafetyRule("minor-carton-scuff", Severity.MINOR, "cosmetic carton damage", ("carton scuff", "outer carton scuff", "cosmetic carton")),
    SafetyRule("minor-printing-blemish", Severity.MINOR, "isolated printing blemish", ("printing blemish", "minor print blemish")),
    SafetyRule("minor-service", Severity.MINOR, "non-quality service issue", ("service complaint", "delivery delay", "late response")),
)


def priority_for_severity(severity: Severity) -> Priority:
    if severity == Severity.CRITICAL:
        return Priority.IMMEDIATE
    if severity == Severity.MAJOR:
        return Priority.HIGH
    if severity == Severity.MINOR:
        return Priority.NORMAL
    return Priority.UNDETERMINED


def highest_severity(values: list[Severity]) -> Severity:
    if not values:
        return Severity.UNDETERMINED
    return max(values, key=lambda item: SEVERITY_RANK[item])


def evaluate_safety_rules(
    complaint: dict[str, object | None],
    classification: DefectClassification,
) -> DeterministicSafetyResult:
    joined = " ".join(str(value) for value in complaint.values() if value not in (None, "", False)).lower()
    category_set = set(classification.categories)
    matches: list[SafetyRuleMatch] = []
    for rule in SAFETY_RULES:
        term_matches = [term for term in rule.terms if term in joined]
        category_matches = [category for category in rule.categories if category in category_set]
        if not term_matches and not category_matches:
            continue
        evidence = ", ".join(term_matches) if term_matches else ", ".join(category.value for category in category_matches)
        matches.append(
            SafetyRuleMatch(
                rule_id=rule.rule_id,
                severity_floor=rule.severity_floor,
                signal=rule.signal,
                evidence=evidence,
            )
        )

    floor = highest_severity([match.severity_floor for match in matches])
    return DeterministicSafetyResult(
        rule_version=SAFETY_RULE_VERSION,
        severity_floor=floor,
        priority_floor=priority_for_severity(floor),
        matches=matches,
    )
