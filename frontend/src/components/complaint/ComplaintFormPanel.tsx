import type { ComplaintDraftState } from "../../types/complaintWorkspace";
import type { DuplicateAnalysisResult } from "../../features/investigationSupport/investigationSupportTypes";
import { StatusBadge } from "../common/StatusBadge";
import { ComplaintFooterActions } from "./ComplaintFooterActions";
import { ComplaintSection } from "./ComplaintSection";
import { ReadOnlyField } from "./ReadOnlyField";
import { RiskAssessmentSection } from "./RiskAssessmentSection";

interface ComplaintFormPanelProps {
  draft: ComplaintDraftState;
  onReset: () => void;
  onSave: () => void;
  errorMessage?: string | null;
  infoMessage?: string | null;
  successMessage?: string | null;
  isResetting?: boolean;
  isSaving?: boolean;
  canSave?: boolean;
  committedComplaintId?: string | null;
  onAskFollowUpQuestions?: (questions: string[]) => void;
  onViewFieldEvidence?: (fieldName: string, label: string) => void;
  duplicateAnalysis?: DuplicateAnalysisResult | null;
  onViewDuplicateDetails?: () => void;
}

export function ComplaintFormPanel({
  draft,
  onReset,
  onSave,
  errorMessage = null,
  infoMessage = null,
  successMessage = null,
  isResetting = false,
  isSaving = false,
  canSave = false,
  committedComplaintId = null,
  onAskFollowUpQuestions,
  onViewFieldEvidence,
  duplicateAnalysis = null,
  onViewDuplicateDetails
}: ComplaintFormPanelProps) {
  const { fields } = draft;
  const strongestDuplicate = duplicateAnalysis?.candidates[0] ?? null;
  function evidenceHandler(fieldName: string | undefined, label: string) {
    if (!fieldName) {
      return undefined;
    }
    return () => onViewFieldEvidence?.(fieldName, label);
  }

  return (
    <section className="complaint-form-panel" data-testid="complaint-form-panel" aria-labelledby="complaint-form-title">
      <header className="complaint-form-header">
        <div>
          <h1 id="complaint-form-title">Log Customer Complaint</h1>
          <p>API & FDF Quality Assurance Module</p>
        </div>
        <StatusBadge tone={draft.statusLabel === "Committed" ? "success" : "warning"}>{draft.statusLabel}</StatusBadge>
      </header>

      {errorMessage ? (
        <div className="complaint-panel-banner complaint-panel-banner--error" role="alert">
          {errorMessage}
        </div>
      ) : null}
      {infoMessage ? (
        <div className="complaint-panel-banner complaint-panel-banner--info" role="status">
          {infoMessage}
        </div>
      ) : null}
      {successMessage ? (
        <div className="complaint-panel-banner complaint-panel-banner--success" role="status">
          {successMessage}
          {committedComplaintId ? (
            <a className="complaint-panel-banner__action" href="/qms-ledger">
              View QMS Ledger
            </a>
          ) : null}
        </div>
      ) : null}

      <div className="complaint-form-content">
        <ComplaintSection number={1} title="ORIGIN & CUSTOMER DETAILS">
          <div className="field-grid field-grid--two">
            <ReadOnlyField id="complaintSource" label="Complaint Source" {...fields.complaintSource} onViewEvidence={evidenceHandler(fields.complaintSource.fieldName, "Complaint Source")} />
            <ReadOnlyField id="customerName" label="Customer Name" {...fields.customerName} onViewEvidence={evidenceHandler(fields.customerName.fieldName, "Customer Name")} />
          </div>
        </ComplaintSection>

        <ComplaintSection number={2} title="PRODUCT & BATCH IDENTIFICATION">
          <div className="field-grid field-grid--two">
            <ReadOnlyField id="productName" label="Product Name" {...fields.productName} onViewEvidence={evidenceHandler(fields.productName.fieldName, "Product Name")} />
            <ReadOnlyField id="productStrengthGrade" label="Product Strength/Grade" {...fields.productStrengthGrade} onViewEvidence={evidenceHandler(fields.productStrengthGrade.fieldName, "Product Strength/Grade")} />
            <ReadOnlyField id="batchLotNumber" label="Batch/Lot Number" {...fields.batchLotNumber} onViewEvidence={evidenceHandler(fields.batchLotNumber.fieldName, "Batch/Lot Number")} />
            <ReadOnlyField id="manufacturingDate" label="Manufacturing Date" {...fields.manufacturingDate} onViewEvidence={evidenceHandler(fields.manufacturingDate.fieldName, "Manufacturing Date")} />
            <ReadOnlyField id="expiryDate" label="Expiry Date" {...fields.expiryDate} onViewEvidence={evidenceHandler(fields.expiryDate.fieldName, "Expiry Date")} />
            <ReadOnlyField id="quantityAffected" label="Quantity Affected" {...fields.quantityAffected} onViewEvidence={evidenceHandler(fields.quantityAffected.fieldName, "Quantity Affected")} />
          </div>
        </ComplaintSection>

        <ComplaintSection number={3} title="COMPLAINT DETAILS">
          <div className="field-grid field-grid--two">
            <ReadOnlyField id="complaintType" label="Complaint Type" {...fields.complaintType} onViewEvidence={evidenceHandler(fields.complaintType.fieldName, "Complaint Type")} />
            <ReadOnlyField id="complaintDate" label="Complaint Date" {...fields.complaintDate} onViewEvidence={evidenceHandler(fields.complaintDate.fieldName, "Complaint Date")} />
          </div>
          <ReadOnlyField
            id="detailedComplaintDescription"
            label="Detailed Complaint Description"
            multiline
            {...fields.detailedComplaintDescription}
            onViewEvidence={evidenceHandler(fields.detailedComplaintDescription.fieldName, "Detailed Complaint Description")}
          />
        </ComplaintSection>

        <RiskAssessmentSection
          fields={fields}
          riskDetails={draft.riskDetails}
          completeness={draft.completeness}
          onAskFollowUpQuestions={onAskFollowUpQuestions}
          onViewFieldEvidence={onViewFieldEvidence}
        />
        {strongestDuplicate ? (
          <div className="duplicate-summary-alert" data-testid="duplicate-summary-alert">
            <div>
              <strong>{duplicateAnalysis?.candidates.length ?? 0} potential duplicate or recurrence candidate(s)</strong>
              <span>
                Strongest: {strongestDuplicate.complaint_number} · {strongestDuplicate.classification.replace(/_/g, " ")}
              </span>
            </div>
            <button type="button" className="button button--secondary" onClick={onViewDuplicateDetails}>
              View details
            </button>
          </div>
        ) : null}
      </div>

      <ComplaintFooterActions
        onReset={onReset}
        onSave={onSave}
        isResetting={isResetting}
        isSaving={isSaving}
        canSave={canSave}
      />
    </section>
  );
}
