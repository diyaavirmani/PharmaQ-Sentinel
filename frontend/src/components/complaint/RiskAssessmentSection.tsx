import { useState } from "react";
import type { CompletenessState, ComplaintDraftFields, RiskDetailsState } from "../../types/complaintWorkspace";
import { ComplaintSection } from "./ComplaintSection";
import { ReadOnlyField } from "./ReadOnlyField";

interface RiskAssessmentSectionProps {
  fields: ComplaintDraftFields;
  riskDetails: RiskDetailsState | null;
  completeness: CompletenessState | null;
  onAskFollowUpQuestions?: (questions: string[]) => void;
  onViewFieldEvidence?: (fieldName: string, label: string) => void;
}

function labelFromEnum(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function RiskDetailsCard({ riskDetails }: { riskDetails: RiskDetailsState }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const confidence =
    riskDetails.confidence !== null ? `${Math.round(Number(riskDetails.confidence) * 100)}% confidence` : "Confidence not provided";
  return (
    <article className="risk-details-card" data-testid="risk-details-card">
      <button
        type="button"
        className="risk-details-card__summary"
        aria-expanded={isExpanded}
        onClick={() => setIsExpanded((current) => !current)}
      >
        <span>{confidence}</span>
        <span>{riskDetails.oneLineRationale ?? "Draft risk rationale not provided."}</span>
      </button>
      <div className="risk-route-chip-row" aria-label="Suggested safety review routes">
        {riskDetails.routeChips.map((route) => (
          <span className="risk-route-chip" key={route}>
            {labelFromEnum(route)}
          </span>
        ))}
        {riskDetails.requiresQaConfirmation ? (
          <span className="risk-route-chip risk-route-chip--qa">Requires QA confirmation</span>
        ) : null}
        {riskDetails.criticalSignals.length ? (
          <span className="risk-route-chip risk-route-chip--critical">Critical signal</span>
        ) : null}
      </div>
      {isExpanded ? (
        <div className="risk-details-card__expanded">
          <RiskDetailList title="Potential hazards" items={riskDetails.potentialHazards} />
          <RiskDetailList title="Supporting evidence" items={riskDetails.supportingEvidence} />
          <RiskDetailList title="Contradictory evidence" items={riskDetails.contradictingEvidence} emptyText="None documented." />
          <RiskDetailList title="Recommended next actions" items={riskDetails.recommendedActions} />
          <RiskDetailList title="Limitations" items={riskDetails.limitations} />
        </div>
      ) : null}
    </article>
  );
}

function RiskDetailList({ title, items, emptyText = "Not provided." }: { title: string; items: string[]; emptyText?: string }) {
  return (
    <div className="risk-detail-list">
      <h3>{title}</h3>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>{emptyText}</p>
      )}
    </div>
  );
}

function CompletenessCard({
  completeness,
  onAskFollowUpQuestions
}: {
  completeness: CompletenessState;
  onAskFollowUpQuestions?: (questions: string[]) => void;
}) {
  return (
    <article className="completeness-card" data-testid="completeness-card">
      <div>
        <strong>{completeness.percentage}% complete</strong>
        <span>{completeness.canBeginTriage ? "Ready for draft triage" : "Needs critical intake details"}</span>
      </div>
      {completeness.missingItems.length ? (
        <p>Missing: {completeness.missingItems.join(", ")}</p>
      ) : (
        <p>No priority missing items are currently shown.</p>
      )}
      {completeness.followUpQuestions.length ? (
        <button type="button" onClick={() => onAskFollowUpQuestions?.(completeness.followUpQuestions)}>
          Ask follow-up questions
        </button>
      ) : null}
    </article>
  );
}

export function RiskAssessmentSection({
  fields,
  riskDetails,
  completeness,
  onAskFollowUpQuestions,
  onViewFieldEvidence
}: RiskAssessmentSectionProps) {
  return (
    <ComplaintSection number={4} title="INITIAL ASSESSMENT & PRIORITY">
      <div className="field-grid field-grid--two">
        <ReadOnlyField
          id="initialSeverity"
          label="Initial Severity"
          {...fields.initialSeverity}
          onViewEvidence={() => fields.initialSeverity.fieldName ? onViewFieldEvidence?.(fields.initialSeverity.fieldName, "Initial Severity") : undefined}
        />
        <ReadOnlyField
          id="priority"
          label="Priority"
          {...fields.priority}
          onViewEvidence={() => fields.priority.fieldName ? onViewFieldEvidence?.(fields.priority.fieldName, "Priority") : undefined}
        />
      </div>
      {riskDetails ? <RiskDetailsCard riskDetails={riskDetails} /> : <div className="risk-reserved-space" aria-hidden="true" />}
      {completeness ? (
        <CompletenessCard completeness={completeness} onAskFollowUpQuestions={onAskFollowUpQuestions} />
      ) : null}
    </ComplaintSection>
  );
}
