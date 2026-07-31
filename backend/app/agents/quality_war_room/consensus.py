from __future__ import annotations

from app.agents.quality_war_room.schemas import AuditorOutput, ConsensusOutput, SpecialistOutput


def build_consensus(
    *,
    complaint: dict,
    specialist_outputs: dict[str, SpecialistOutput],
    auditor_output: AuditorOutput,
) -> ConsensusOutput:
    complete_outputs = [output for output in specialist_outputs.values() if output.status == "COMPLETE"]
    severity = complaint.get("suggested_severity") or "UNDETERMINED"
    priority = complaint.get("suggested_priority") or "UNDETERMINED"
    route = complaint.get("safety_route") or "UNDETERMINED"
    evidence_ids = sorted({evidence_id for output in complete_outputs for evidence_id in output.evidence_ids})
    hypotheses = [
        hypothesis
        for output in complete_outputs
        for hypothesis in output.hypotheses
        if hypothesis not in auditor_output.rejected_claims
    ]
    recommended_checks = [check for output in complete_outputs for check in output.recommended_checks]
    immediate = [item for output in complete_outputs for item in output.immediate_considerations]
    open_questions = [question for output in complete_outputs for question in output.open_questions]
    unavailable = [
        output.agent_name for output in specialist_outputs.values() if output.status != "COMPLETE"
    ]
    disagreements = list(auditor_output.challenged_findings)
    if unavailable:
        disagreements.append(f"Unavailable specialist output: {', '.join(unavailable)}.")

    return ConsensusOutput(
        suggested_severity=severity,
        suggested_priority=priority,
        recommended_routes=[route],
        immediate_containment_considerations=immediate[:6],
        investigation_priorities=recommended_checks[:8],
        root_cause_hypotheses=hypotheses[:6],
        confirmation_tests=[
            "Compare complaint sample, retain sample and batch records where available.",
            "Document evidence gaps before any final quality decision.",
            *recommended_checks[:4],
        ],
        CAPA_considerations={
            "containment": ["Consider whether inventory assessment or hold review is warranted."],
            "correction": ["Define correction options only after QA confirms the issue scope."],
            "corrective_action": ["Assess whether a procedural or process action is justified after investigation."],
            "preventive_action": ["Review trend controls if recurrence is confirmed."],
            "effectiveness_check": ["Define objective effectiveness criteria if a CAPA is opened by QA."],
        },
        agent_agreements=auditor_output.accepted_findings[:8],
        agent_disagreements=disagreements,
        rejected_unsupported_claims=auditor_output.rejected_claims,
        unresolved_questions=open_questions[:8],
        evidence_ids=evidence_ids,
        limitations=[
            "This War Room run is deterministic decision support and not an authorized quality decision.",
            "Seeded reference data is fictional demonstration data.",
            *auditor_output.compliance_warnings,
        ],
        human_approval_required=True,
    )
