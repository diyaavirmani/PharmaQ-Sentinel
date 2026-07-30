import type { ComplaintDraftFields } from "../../types/complaintWorkspace";
import { ComplaintSection } from "./ComplaintSection";
import { ReadOnlyField } from "./ReadOnlyField";

interface RiskAssessmentSectionProps {
  fields: ComplaintDraftFields;
}

export function RiskAssessmentSection({ fields }: RiskAssessmentSectionProps) {
  return (
    <ComplaintSection number={4} title="INITIAL ASSESSMENT & PRIORITY">
      <div className="field-grid field-grid--two">
        <ReadOnlyField id="initialSeverity" label="Initial Severity" {...fields.initialSeverity} />
        <ReadOnlyField id="priority" label="Priority" {...fields.priority} />
      </div>
      <div className="risk-reserved-space" aria-hidden="true" />
    </ComplaintSection>
  );
}
