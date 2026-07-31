from __future__ import annotations

from app.agents.quality_war_room.constants import (
    MAX_REVISION_REQUESTS_PER_SPECIALIST,
    PROHIBITED_FINALITY_TERMS,
)
from app.agents.quality_war_room.schemas import AuditorOutput, SpecialistOutput


def _contains_finality(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in PROHIBITED_FINALITY_TERMS)


def run_compliance_auditor(outputs: dict[str, SpecialistOutput], *, revision_counts: dict[str, int] | None = None) -> AuditorOutput:
    accepted: list[str] = []
    challenged: list[str] = []
    rejected: list[str] = []
    missing: list[str] = []
    contradictions: list[str] = []
    revision_requests: dict[str, list[str]] = {}
    revision_counts = revision_counts or {}

    for key, output in outputs.items():
        if output.status != "COMPLETE":
            missing.append(f"{output.agent_name} output is unavailable: {output.status}.")
            continue
        accepted.extend(output.concise_findings[:2])
        contradictions.extend(output.contradictions)
        combined_claims = [*output.concise_findings, *output.hypotheses, *output.immediate_considerations]
        finality_claims = [claim for claim in combined_claims if _contains_finality(claim)]
        if finality_claims:
            rejected.extend(finality_claims)
            challenged.append(f"{output.agent_name} used final causation or authorization language.")
            if revision_counts.get(key, 0) < MAX_REVISION_REQUESTS_PER_SPECIALIST:
                revision_requests[key] = ["Remove final causation language and restate as evidence-backed hypotheses."]
        if not output.evidence_ids:
            missing.append(f"{output.agent_name} did not cite field evidence IDs; use available source records where possible.")

    return AuditorOutput(
        accepted_findings=accepted[:8],
        challenged_findings=challenged,
        rejected_claims=rejected,
        missing_evidence=missing,
        contradiction_findings=contradictions,
        specialist_revision_requests=revision_requests,
        compliance_warnings=[
            "AI output is a draft recommendation only.",
            "Human QA approval is required before any official severity, root-cause, CAPA or regulatory decision.",
        ],
    )
