from __future__ import annotations

from dataclasses import dataclass

from app.services.quality.schemas import DefectCategory, DefectClassification


@dataclass(frozen=True)
class DefectRule:
    category: DefectCategory
    terms: tuple[str, ...]


DEFECT_TAXONOMY_VERSION = "defect-taxonomy-v1"
DEFECT_RULES: tuple[DefectRule, ...] = (
    DefectRule(DefectCategory.PRODUCT_APPEARANCE, ("discoloured", "discolored", "colour variation", "color variation")),
    DefectRule(DefectCategory.PACKAGING_LEAKAGE, ("blister leakage", "leaking blister", "compromised seal", "seal leak")),
    DefectRule(DefectCategory.BROKEN_OR_DAMAGED_DOSAGE_FORM, ("broken tablet", "broken capsule", "damaged dosage")),
    DefectRule(DefectCategory.INCORRECT_LABEL, ("wrong label", "incorrect label", "label information error")),
    DefectRule(DefectCategory.WRONG_PRODUCT, ("wrong product", "product mix-up", "mix up", "mixed up")),
    DefectRule(DefectCategory.WRONG_STRENGTH, ("wrong strength", "incorrect strength", "wrong potency")),
    DefectRule(DefectCategory.MISSING_QUANTITY, ("missing tablet", "missing capsule", "short count", "missing quantity")),
    DefectRule(DefectCategory.FOREIGN_MATTER, ("foreign particle", "foreign matter", "glass particle", "metal particle")),
    DefectRule(DefectCategory.CONTAMINATION, ("contamination", "contaminated", "microbial contamination")),
    DefectRule(DefectCategory.STERILITY_CONCERN, ("sterility", "sterile failure", "non-sterile", "vial leakage")),
    DefectRule(DefectCategory.API_ASSAY_DISCREPANCY, ("api assay", "assay discrepancy", "assay failure")),
    DefectRule(DefectCategory.API_IMPURITY_DISCREPANCY, ("impurity discrepancy", "unknown impurity", "impurity failure")),
    DefectRule(DefectCategory.API_MOISTURE_DISCREPANCY, ("moisture discrepancy", "high moisture", "water content")),
    DefectRule(DefectCategory.CONTAINER_DAMAGE, ("damaged container", "container damage", "drum damage")),
    DefectRule(DefectCategory.STORAGE_OR_TRANSPORTATION, ("temperature excursion", "storage condition", "transportation")),
    DefectRule(DefectCategory.LACK_OF_EFFECT, ("lack of effect", "no effect", "ineffective")),
    DefectRule(DefectCategory.ADVERSE_REACTION, ("patient reaction", "swelling", "rash", "hospital treatment", "serious outcome")),
    DefectRule(DefectCategory.SUSPECTED_COUNTERFEIT_OR_TAMPERING, ("counterfeit", "tamper", "tampering", "fake product")),
    DefectRule(DefectCategory.SERVICE_COMPLAINT, ("late response", "service complaint", "billing", "delivery delay")),
)


def classify_defects(complaint: dict[str, object | None]) -> DefectClassification:
    text = " ".join(
        str(value)
        for key, value in complaint.items()
        if key != "missing_fields" and value not in (None, "", False)
    ).lower()
    categories: list[DefectCategory] = []
    evidence_terms: dict[str, list[str]] = {}
    for rule in DEFECT_RULES:
        matches = [term for term in rule.terms if term in text]
        if matches:
            categories.append(rule.category)
            evidence_terms[rule.category.value] = matches

    if not categories:
        categories.append(DefectCategory.UNKNOWN)
    return DefectClassification(categories=categories, evidence_terms=evidence_terms)
