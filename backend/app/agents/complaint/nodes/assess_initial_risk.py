from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import select

from app.agents.complaint.constants import ComplaintAssistantIntent
from app.agents.complaint.state import ComplaintAssistantState
from app.models import ActorType, ExtractionStatus, FieldEvidence
from app.models.base import utc_now
from app.repositories import (
    AuditEventRepository,
    ComplaintAttachmentRepository,
    ComplaintDraftRepository,
    RiskAssessmentVersionRepository,
)
from app.schemas.complaints import ComplaintDraftResponse
from app.services.quality import assess_pharma_risk, draft_risk_patch
from app.services.quality.schemas import HybridRiskAssessment

RISK_RELEVANT_FIELDS = {
    "product_type",
    "product_name",
    "product_strength_grade",
    "dosage_form",
    "batch_lot_number",
    "quantity_affected",
    "quantity_unit",
    "complaint_type",
    "detailed_description",
    "defect_observed_date",
    "sample_available",
    "patient_consumed_product",
    "adverse_event_signal",
    "counterfeit_signal",
    "storage_conditions",
    "safety_route",
}
FIELD_LABELS = {
    "batch_lot_number": "Batch/Lot Number",
    "quantity_affected": "Quantity Affected",
    "quantity_unit": "Quantity Unit",
    "customer_contact": "Customer Contact",
    "storage_conditions": "Storage Conditions",
}


def _serialise_value(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def _assistant_confirmation(
    *,
    complaint: dict[str, object | None],
    changed_fields: list[str],
    conflict_fields: list[str],
    missing_fields: list[str],
    assessment: HybridRiskAssessment | None,
    is_document: bool = False,
) -> str:
    if not changed_fields:
        response = "I could not add new complaint fields from that message."
    elif is_document:
        response = "Document text was extracted and added to the draft."
    else:
        response = "Complaint details were extracted and added to the draft."
    lines = [response]
    product = complaint.get("product_name")
    strength = complaint.get("product_strength_grade")
    if product:
        lines.append(f"Product: {product}{f' {strength}' if strength else ''}")
    if complaint.get("batch_lot_number"):
        lines.append(f"Batch: {complaint['batch_lot_number']}")
    if complaint.get("quantity_affected"):
        quantity_line = f"Quantity affected: {complaint['quantity_affected']}"
        if complaint.get("quantity_unit"):
            quantity_line += f" {complaint['quantity_unit']}"
        lines.append(quantity_line)
    if assessment:
        lines.append(f"Suggested severity: {assessment.assessment.suggested_severity.value.title()}")
        route_labels = ", ".join(route.value.replace("_", " ").title() for route in assessment.routing.routes[:2])
        if route_labels:
            lines.append(f"Suggested review route: {route_labels}.")
    if missing_fields:
        concise_missing = " and ".join(missing_fields[:2])
        lines.append(f"I still need {concise_missing}.")
    if conflict_fields:
        lines.append("I found conflicting values and kept the existing draft fields for QA clarification.")
    if assessment:
        lines.append("This requires QA confirmation; risk and route outputs are draft suggestions.")
    return "\n".join(lines)


def _edit_confirmation(
    *,
    changed_fields: list[str],
    no_op_fields: list[str],
    old_values: dict[str, object | None],
    complaint: dict[str, object | None],
) -> str:
    if changed_fields:
        changes = []
        for field_name in changed_fields:
            if field_name.startswith("suggested_") or field_name in {
                "safety_route",
                "risk_rationale",
                "potential_hazard",
                "suggested_next_action",
                "risk_confidence",
                "missing_fields",
            }:
                continue
            label = FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())
            old_value = old_values.get(field_name)
            new_value = complaint.get(field_name)
            if old_value in (None, ""):
                changes.append(f"added {label} as {new_value}")
            elif new_value in (None, ""):
                changes.append(f"cleared {label}")
            else:
                suffix = ""
                if field_name == "quantity_affected" and complaint.get("quantity_unit"):
                    suffix = f" {complaint['quantity_unit']}"
                changes.append(f"updated {label} from {old_value} to {new_value}{suffix}")
        if changes:
            sentence = " and ".join(changes)
            return f"{sentence[0].upper()}{sentence[1:]}. All other complaint information was preserved."

    if no_op_fields:
        label = FIELD_LABELS.get(no_op_fields[0], no_op_fields[0].replace("_", " ").title())
        value = complaint.get(no_op_fields[0])
        return f"{label} is already {value}. No change was required."

    return "I did not find a supported explicit correction to apply. All complaint information was preserved."


def _risk_event_type(intent: str) -> str:
    if intent == ComplaintAssistantIntent.EDIT_COMPLAINT.value:
        return "EDIT_COMPLAINT_FIELD_CHANGED"
    if intent == ComplaintAssistantIntent.EXTRACT_DOCUMENT.value:
        return "DOCUMENT_EXTRACTION_FIELD_CHANGED"
    return "LOG_COMPLAINT_FIELD_CHANGED"


def _risk_tool_name(intent: str) -> str:
    if intent == ComplaintAssistantIntent.EDIT_COMPLAINT.value:
        return "EDIT_COMPLAINT"
    if intent == ComplaintAssistantIntent.EXTRACT_DOCUMENT.value:
        return "EXTRACT_DOCUMENT"
    return "LOG_COMPLAINT"


def _risk_reason(intent: str) -> str:
    if intent == ComplaintAssistantIntent.EDIT_COMPLAINT.value:
        return "User correction through AI Complaint Intake Assistant"
    if intent == ComplaintAssistantIntent.EXTRACT_DOCUMENT.value:
        return "Document extraction through AI Complaint Intake Assistant"
    return "Initial complaint extraction"


def _with_edit_response(state: ComplaintAssistantState) -> ComplaintAssistantState:
    if state.get("assistant_response"):
        return state
    response = _edit_confirmation(
        changed_fields=state["changed_fields"],
        no_op_fields=state["no_op_fields"],
        old_values=state.get("pre_merge_complaint", state["existing_complaint"]),
        complaint=state["existing_complaint"],
    )
    return {**state, "assistant_response": response}


def _active_evidence_ids(runtime: Any, draft_id: str) -> list[str]:
    statement = select(FieldEvidence.id).where(FieldEvidence.draft_id == draft_id, FieldEvidence.is_active.is_(True))
    return list(runtime.db.scalars(statement).all())


def assess_initial_risk_node(runtime: Any):
    def complete_document_attachment(
        state: ComplaintAssistantState,
        *,
        failed: bool = False,
        error: str | None = None,
    ) -> None:
        attachment_id = state.get("attachment_id")
        if not attachment_id:
            return
        attachment_repository = ComplaintAttachmentRepository(runtime.db)
        attachment = attachment_repository.get_for_draft(state["draft_id"], attachment_id)
        if not attachment:
            return
        if failed:
            attachment_repository.update_extraction_state(
                attachment,
                status=ExtractionStatus.FAILED,
                stage="FAILED",
                progress=100,
                error=error or "Document extraction failed.",
                completed_at=utc_now(),
            )
            return
        attachment_repository.update_extraction_state(
            attachment,
            status=ExtractionStatus.COMPLETE,
            stage="COMPLETE",
            progress=100,
            completed_at=utc_now(),
        )

    def node(state: ComplaintAssistantState) -> ComplaintAssistantState:
        if state["errors"]:
            if state.get("intent") == ComplaintAssistantIntent.EXTRACT_DOCUMENT.value:
                complete_document_attachment(state, failed=True, error="Document extraction failed before completion.")
            return state
        if state["intent"] not in {
            ComplaintAssistantIntent.LOG_COMPLAINT.value,
            ComplaintAssistantIntent.EDIT_COMPLAINT.value,
            ComplaintAssistantIntent.EXTRACT_DOCUMENT.value,
        }:
            return {**state, "initial_risk_assessment": None}

        is_edit = state["intent"] == ComplaintAssistantIntent.EDIT_COMPLAINT.value
        is_document = state["intent"] == ComplaintAssistantIntent.EXTRACT_DOCUMENT.value
        risk_affecting_change = not is_edit or any(field in RISK_RELEVANT_FIELDS for field in state["changed_fields"])
        if is_edit and not risk_affecting_change:
            return _with_edit_response(state)
        if is_document and state.get("attachment_id"):
            attachment_repository = ComplaintAttachmentRepository(runtime.db)
            attachment = attachment_repository.get_for_draft(state["draft_id"], state["attachment_id"])
            if attachment:
                attachment_repository.update_extraction_state(
                    attachment,
                    stage="ASSESSING_RISK",
                    progress=90,
                )

        assessment = assess_pharma_risk(
            complaint=state["existing_complaint"],
            latest_user_message=state["latest_user_message"],
            changed_fields=state["changed_fields"],
            request_id=state["request_id"],
            draft_id=state["draft_id"],
            thread_id=state["thread_id"],
            llm_gateway=runtime.llm_gateway,
        )
        if is_edit and assessment.provider_name is None and any(
            state["existing_complaint"].get(field_name)
            for field_name in (
                "suggested_severity",
                "suggested_priority",
                "risk_rationale",
                "potential_hazard",
                "suggested_next_action",
                "risk_confidence",
            )
        ):
            return _with_edit_response(
                {
                    **state,
                    "completeness_result": assessment.completeness.model_dump(mode="json"),
                    "safety_routing_result": assessment.routing.model_dump(mode="json"),
                    "defect_classification_result": assessment.defect_classification.model_dump(mode="json"),
                    "deterministic_safety_result": assessment.deterministic.model_dump(mode="json"),
                    "warnings": [*state["warnings"], *assessment.warnings],
                }
            )
        warnings = [*state["warnings"], *assessment.warnings]
        prompt_versions = {
            **state["prompt_versions"],
            "pharma_risk": assessment.prompt_version,
            "safety_rules": assessment.deterministic.rule_version,
        }

        draft = ComplaintDraftRepository(runtime.db).get_required(state["draft_id"])
        risk_patch = draft_risk_patch(assessment)
        audit_repository = AuditEventRepository(runtime.db)
        changed_fields = list(state["changed_fields"])
        for field_name, new_value in risk_patch.items():
            old_value = getattr(draft, field_name)
            if _serialise_value(old_value) == _serialise_value(new_value):
                continue
            setattr(draft, field_name, new_value)
            changed_fields.append(field_name)
            audit_repository.append(
                draft_id=draft.id,
                event_type=_risk_event_type(state["intent"]),
                actor_type=ActorType.AI_AGENT,
                actor_identifier="Complaint Intake Assistant",
                tool_name=_risk_tool_name(state["intent"]),
                field_name=field_name,
                old_value={"value": _serialise_value(old_value)},
                new_value={"value": _serialise_value(new_value)},
                reason=_risk_reason(state["intent"]),
                provider_name=assessment.provider_name,
                requested_model=assessment.requested_model,
                actual_model=assessment.actual_model,
                metadata_json={
                    "source": "pharma_risk_assessment",
                    "request_id": state["request_id"],
                    "source_attachment_id": state.get("attachment_id"),
                    "deterministic_severity_floor": assessment.deterministic.severity_floor.value,
                    "requires_qa_confirmation": True,
                },
            )

        evidence_ids = _active_evidence_ids(runtime, draft.id)
        supporting_evidence = {
            "rule_version": assessment.deterministic.rule_version,
            "prompt_version": assessment.prompt_version,
            "completeness_version": "complaint-completeness-v1",
            "defect_taxonomy_version": "defect-taxonomy-v1",
            "safety_router_version": "safety-router-v1",
            "evidence_ids": evidence_ids,
            "deterministic_severity_floor": assessment.deterministic.severity_floor.value,
            "deterministic_rule_matches": [match.model_dump(mode="json") for match in assessment.deterministic.matches],
            "contextual_assessment": assessment.assessment.model_dump(mode="json"),
            "final_suggested_result": {
                "severity": assessment.assessment.suggested_severity.value,
                "priority": assessment.assessment.suggested_priority.value,
                "routes": [route.value for route in assessment.routing.routes],
                "case_type": assessment.routing.case_type.value,
            },
            "material_fingerprint": assessment.material_fingerprint,
        }
        risk_repository = RiskAssessmentVersionRepository(runtime.db)
        latest = risk_repository.get_latest_for_draft(draft.id)
        assessment_changed = (
            latest is None
            or latest.severity != assessment.assessment.suggested_severity.value
            or latest.priority != assessment.assessment.suggested_priority.value
            or latest.safety_route != assessment.routing.case_type.value
            or (latest.supporting_evidence or {}).get("material_fingerprint") != assessment.material_fingerprint
        )
        if assessment_changed and risk_affecting_change:
            risk_repository.append(
                draft_id=draft.id,
                version_number=1 if latest is None else latest.version_number + 1,
                severity=assessment.assessment.suggested_severity,
                priority=assessment.assessment.suggested_priority,
                patient_harm_level=assessment.assessment.patient_harm_level,
                safety_route=assessment.routing.case_type.value,
                risk_rationale=assessment.assessment.rationale,
                potential_hazard="; ".join(assessment.assessment.potential_hazards) or None,
                suggested_next_action="; ".join(assessment.assessment.recommended_actions) or None,
                confidence=Decimal(str(assessment.assessment.confidence)),
                supporting_evidence=supporting_evidence,
                contradicting_evidence={
                    "items": assessment.assessment.contradicting_evidence,
                    "warnings": warnings,
                },
                provider_name=assessment.provider_name,
                requested_model=assessment.requested_model,
                actual_model=assessment.actual_model,
            )
        draft.updated_at = utc_now()
        if is_document:
            complete_document_attachment(state)
        runtime.db.flush()
        refreshed = ComplaintDraftResponse.model_validate(draft).model_dump(mode="json")
        if is_edit:
            response = _edit_confirmation(
                changed_fields=changed_fields,
                no_op_fields=state["no_op_fields"],
                old_values=state.get("pre_merge_complaint", state["existing_complaint"]),
                complaint=refreshed,
            )
        else:
            response = _assistant_confirmation(
                complaint=refreshed,
                changed_fields=changed_fields,
                conflict_fields=state["conflict_fields"],
                missing_fields=[*assessment.completeness.missing_critical_fields, *assessment.completeness.missing_recommended_fields],
                assessment=assessment,
                is_document=is_document,
            )
        return {
            **state,
            "existing_complaint": refreshed,
            "changed_fields": changed_fields,
            "missing_fields": [*assessment.completeness.missing_critical_fields, *assessment.completeness.missing_recommended_fields],
            "initial_risk_assessment": assessment.assessment.model_dump(mode="json"),
            "completeness_result": assessment.completeness.model_dump(mode="json"),
            "safety_routing_result": assessment.routing.model_dump(mode="json"),
            "defect_classification_result": assessment.defect_classification.model_dump(mode="json"),
            "deterministic_safety_result": assessment.deterministic.model_dump(mode="json"),
            "assistant_response": response,
            "provider": assessment.provider_name,
            "requested_model": assessment.requested_model,
            "actual_model": assessment.actual_model,
            "prompt_versions": prompt_versions,
            "warnings": warnings,
        }

    return node
