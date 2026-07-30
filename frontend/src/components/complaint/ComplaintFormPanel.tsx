import type { ComplaintDraftState } from "../../types/complaintWorkspace";
import { StatusBadge } from "../common/StatusBadge";
import { ComplaintFooterActions } from "./ComplaintFooterActions";
import { ComplaintSection } from "./ComplaintSection";
import { ReadOnlyField } from "./ReadOnlyField";
import { RiskAssessmentSection } from "./RiskAssessmentSection";

interface ComplaintFormPanelProps {
  draft: ComplaintDraftState;
  onReset: () => void;
  errorMessage?: string | null;
  infoMessage?: string | null;
  successMessage?: string | null;
  isResetting?: boolean;
}

export function ComplaintFormPanel({
  draft,
  onReset,
  errorMessage = null,
  infoMessage = null,
  successMessage = null,
  isResetting = false
}: ComplaintFormPanelProps) {
  const { fields } = draft;

  return (
    <section className="complaint-form-panel" data-testid="complaint-form-panel" aria-labelledby="complaint-form-title">
      <header className="complaint-form-header">
        <div>
          <h1 id="complaint-form-title">Log Customer Complaint</h1>
          <p>API & FDF Quality Assurance Module</p>
        </div>
        <StatusBadge tone="warning">{draft.statusLabel}</StatusBadge>
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
        </div>
      ) : null}

      <div className="complaint-form-content">
        <ComplaintSection number={1} title="ORIGIN & CUSTOMER DETAILS">
          <div className="field-grid field-grid--two">
            <ReadOnlyField id="complaintSource" label="Complaint Source" {...fields.complaintSource} />
            <ReadOnlyField id="customerName" label="Customer Name" {...fields.customerName} />
          </div>
        </ComplaintSection>

        <ComplaintSection number={2} title="PRODUCT & BATCH IDENTIFICATION">
          <div className="field-grid field-grid--two">
            <ReadOnlyField id="productName" label="Product Name" {...fields.productName} />
            <ReadOnlyField id="productStrengthGrade" label="Product Strength/Grade" {...fields.productStrengthGrade} />
            <ReadOnlyField id="batchLotNumber" label="Batch/Lot Number" {...fields.batchLotNumber} />
            <ReadOnlyField id="manufacturingDate" label="Manufacturing Date" {...fields.manufacturingDate} />
            <ReadOnlyField id="expiryDate" label="Expiry Date" {...fields.expiryDate} />
            <ReadOnlyField id="quantityAffected" label="Quantity Affected" {...fields.quantityAffected} />
          </div>
        </ComplaintSection>

        <ComplaintSection number={3} title="COMPLAINT DETAILS">
          <div className="field-grid field-grid--two">
            <ReadOnlyField id="complaintType" label="Complaint Type" {...fields.complaintType} />
            <ReadOnlyField id="complaintDate" label="Complaint Date" {...fields.complaintDate} />
          </div>
          <ReadOnlyField
            id="detailedComplaintDescription"
            label="Detailed Complaint Description"
            multiline
            {...fields.detailedComplaintDescription}
          />
        </ComplaintSection>

        <RiskAssessmentSection fields={fields} />
      </div>

      <ComplaintFooterActions onReset={onReset} isResetting={isResetting} />
    </section>
  );
}
