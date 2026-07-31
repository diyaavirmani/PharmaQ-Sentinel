import { useState } from "react";
import { Clipboard, Download, FileText } from "lucide-react";
import { OverlayDrawer } from "../../components/common/OverlayDrawer";
import { getApiBaseUrl } from "../../services/apiClient";
import { useGetInspectionBriefQuery } from "../complaint/complaintApi";
import type { InspectionBrief } from "./inspectionBriefTypes";

interface InspectionBriefActionsProps {
  complaintId?: string | null;
}

function safeErrorMessage(error: unknown) {
  if (typeof error === "object" && error !== null && "status" in error) {
    return "Inspection brief is available only after the complaint is saved.";
  }
  return "Inspection brief action failed. Please retry.";
}

async function copyText(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "true");
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  document.body.appendChild(textArea);
  textArea.select();
  document.execCommand("copy");
  textArea.remove();
}

export function InspectionBriefActions({ complaintId = null }: InspectionBriefActionsProps) {
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const briefQuery = useGetInspectionBriefQuery(complaintId ?? "", { skip: !complaintId });

  async function fetchBrief(format: "json" | "html" | "pdf") {
    if (!complaintId) {
      throw new Error("Complaint must be saved before generating an inspection brief.");
    }
    const response = await fetch(`${getApiBaseUrl()}/complaints/${complaintId}/inspection-brief?format=${format}`, {
      headers: {
        Accept: format === "html" ? "text/html" : format === "pdf" ? "application/pdf" : "application/json"
      }
    });
    if (!response.ok) {
      throw new Error("Inspection brief request failed.");
    }
    return response;
  }

  async function handlePreview() {
    setActionError(null);
    setStatusMessage(null);
    setIsPreviewLoading(true);
    try {
      const response = await fetchBrief("html");
      setPreviewHtml(await response.text());
    } catch (error) {
      setActionError(safeErrorMessage(error));
    } finally {
      setIsPreviewLoading(false);
    }
  }

  async function handleDownload() {
    setActionError(null);
    setStatusMessage(null);
    setIsDownloading(true);
    try {
      const response = await fetchBrief("pdf");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${briefQuery.data?.document_identifier ?? "inspection-brief"}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      setStatusMessage("Inspection brief PDF download started.");
    } catch (error) {
      setActionError(safeErrorMessage(error));
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleCopySummary() {
    setActionError(null);
    setStatusMessage(null);
    try {
      const brief: InspectionBrief =
        briefQuery.data ?? await fetchBrief("json").then((response) => response.json());
      const identification = brief.sections.find((section) => section.title === "Complaint Identification");
      const classification = brief.sections.find((section) => section.title === "Classification");
      const summary = [
        `${brief.complaint_number} inspection brief`,
        `Version: ${brief.version_number}`,
        ...(identification?.fields.map((field) => `${field.label}: ${String(field.value)}`) ?? []),
        ...(classification?.fields.map((field) => `${field.label}: ${String(field.value)}`) ?? []),
        `Snapshot checksum: ${brief.snapshot_checksum}`,
        "AI-generated recommendations require authorised QA review."
      ].join("\n");
      await copyText(summary);
      setStatusMessage("Complaint summary copied.");
    } catch (error) {
      setActionError(safeErrorMessage(error));
    }
  }

  return (
    <section className="inspection-brief-actions" data-testid="inspection-brief-actions">
      <div>
        <span>INSPECTION BRIEF</span>
        <h4>Saved Complaint Brief</h4>
        <p>Preview and export actions use the saved immutable complaint version.</p>
      </div>
      {!complaintId ? (
        <div className="complaint-panel-banner complaint-panel-banner--info">
          Save the complaint before generating an inspection brief.
        </div>
      ) : null}
      <div className="inspection-brief-actions__buttons">
        <button type="button" className="button button--secondary" disabled={!complaintId || isPreviewLoading} onClick={handlePreview}>
          <FileText size={16} aria-hidden="true" />
          {isPreviewLoading ? "Loading..." : "Preview Inspection Brief"}
        </button>
        <button type="button" className="button button--secondary" disabled={!complaintId || isDownloading} onClick={handleDownload}>
          <Download size={16} aria-hidden="true" />
          {isDownloading ? "Preparing..." : "Download PDF"}
        </button>
        <button type="button" className="button button--secondary" disabled={!complaintId} onClick={handleCopySummary}>
          <Clipboard size={16} aria-hidden="true" />
          Copy Complaint Summary
        </button>
      </div>
      {briefQuery.error ? <div className="complaint-panel-banner complaint-panel-banner--error">{safeErrorMessage(briefQuery.error)}</div> : null}
      {actionError ? <div className="complaint-panel-banner complaint-panel-banner--error">{actionError}</div> : null}
      {statusMessage ? <div className="complaint-panel-banner complaint-panel-banner--success">{statusMessage}</div> : null}
      <OverlayDrawer
        title="Inspection Brief Preview"
        isOpen={Boolean(previewHtml)}
        onClose={() => setPreviewHtml(null)}
      >
        {previewHtml ? (
          <iframe
            title="Inspection Brief Preview"
            className="inspection-brief-preview-frame"
            sandbox=""
            srcDoc={previewHtml}
          />
        ) : null}
      </OverlayDrawer>
    </section>
  );
}
