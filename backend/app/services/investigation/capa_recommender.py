from __future__ import annotations

from app.services.investigation.schemas import PlaybookStep


def capa_considerations(category: str) -> dict[str, list[PlaybookStep]]:
    return {
        "containment": [
            PlaybookStep(
                id=f"{category}-capa-containment",
                title="Assess containment need",
                rationale="QA may consider inventory or market assessment after evidence review.",
                owner_hint="QA",
                limitation="Does not create or approve a CAPA.",
            )
        ],
        "correction": [
            PlaybookStep(
                id=f"{category}-capa-correction",
                title="Define correction options",
                rationale="Correction should address confirmed affected units only after review.",
                owner_hint="QA / Operations",
                limitation="Correction is not authorized by this recommendation.",
            )
        ],
        "corrective_action": [
            PlaybookStep(
                id=f"{category}-capa-corrective",
                title="Evaluate corrective action need",
                rationale="A corrective action may be considered if investigation supports a repeatable failure mode.",
                owner_hint="QA",
                limitation="Potential action only; no root cause is confirmed.",
            )
        ],
        "preventive_action": [
            PlaybookStep(
                id=f"{category}-capa-preventive",
                title="Evaluate preventive control",
                rationale="Preventive controls may be considered if trend review indicates broader exposure.",
                owner_hint="QA / Process Owner",
                limitation="Trend signal requires human confirmation.",
            )
        ],
        "effectiveness_check": [
            PlaybookStep(
                id=f"{category}-capa-effectiveness",
                title="Draft effectiveness criteria",
                rationale="If a CAPA is opened, objective effectiveness checks should be defined.",
                owner_hint="QA",
                limitation="Only an input to reviewer notes.",
            )
        ],
    }
