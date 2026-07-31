from __future__ import annotations

from app.services.investigation.schemas import PlaybookStep


def _step(category: str, suffix: str, title: str, rationale: str, owner: str = "QA") -> PlaybookStep:
    return PlaybookStep(
        id=f"{category}-{suffix}",
        title=title,
        rationale=rationale,
        owner_hint=owner,
        limitation="Investigation support only; human QA approval is required.",
    )


PLAYBOOK_ALIASES = {
    "capsule discolouration": "discolouration",
    "discoloration": "discolouration",
    "broken tablets": "broken_tablets",
    "missing tablets": "missing_tablets",
    "blister leakage": "blister_leakage",
    "wrong label": "wrong_label",
    "foreign particles": "foreign_particles",
    "api assay discrepancy": "api_assay_discrepancy",
    "api moisture discrepancy": "api_moisture_discrepancy",
    "damaged container": "damaged_container",
    "suspected adverse event": "adverse_event_quality_overlap",
    "suspected counterfeit": "counterfeit_or_tampering",
    "tampering": "counterfeit_or_tampering",
}

DEFAULT_CATEGORY = "general_quality_complaint"


def resolve_category(complaint_type: str | None, description: str | None = None) -> str:
    haystack = f"{complaint_type or ''} {description or ''}".lower()
    for term, category in PLAYBOOK_ALIASES.items():
        if term in haystack:
            return category
    return DEFAULT_CATEGORY


def playbook_steps(category: str) -> tuple[list[PlaybookStep], list[PlaybookStep], list[PlaybookStep]]:
    common_containment = [
        _step(category, "containment-samples", "Preserve samples and attachments", "Complaint and retain samples should remain traceable for QA review."),
        _step(category, "containment-inventory", "Assess inventory review need", "Remaining inventory may need assessment if the batch or packaging context is implicated."),
    ]
    category_checks = {
        "discolouration": [
            _step(category, "visual-comparison", "Compare visual appearance", "Compare complaint sample, retain sample and approved description."),
            _step(category, "storage-review", "Review storage exposure", "Temperature, humidity or light exposure may be relevant hypotheses."),
        ],
        "api_assay_discrepancy": [
            _step(category, "assay-method", "Review assay method and chromatograms", "Method, standard and analyst records can clarify an assay discrepancy."),
            _step(category, "material-coa", "Compare supplier and release data", "API supplier lot and release records may be relevant context."),
        ],
        "adverse_event_quality_overlap": [
            _step(category, "pv-minimum", "Check PV minimum criteria", "PV triage may need patient, reporter, event and product details."),
            _step(category, "quality-sample", "Continue quality sample review", "Quality investigation should continue alongside PV routing."),
        ],
        "counterfeit_or_tampering": [
            _step(category, "chain-custody", "Preserve chain of custody", "Tampering or counterfeit signals require controlled evidence handling."),
            _step(category, "pack-authenticity", "Check packaging authenticity markers", "Label, serialization or pack features may need comparison."),
        ],
    }
    investigation = category_checks.get(
        category,
        [
            _step(category, "batch-record", "Review batch record", "Batch documentation can identify relevant checks and gaps."),
            _step(category, "retain-sample", "Review retain sample", "Retain sample comparison may support or contradict the complaint observation."),
        ],
    )
    hypotheses = [
        _step(category, "hypothesis-process", "Potential process-related factor", "Evaluate only if batch, equipment or deviation evidence supports it."),
        _step(category, "hypothesis-material", "Potential material or packaging factor", "Evaluate only if lot and supplier records support it."),
    ]
    return common_containment, investigation, hypotheses
