import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { afterEach, describe, expect, test, vi } from "vitest";
import { App } from "./App";
import { createAppStore, type RootState } from "./app/store";
import type { ComplaintDraftResponse } from "./features/complaint/complaintTypes";

function makeDraft(overrides: Partial<ComplaintDraftResponse> = {}): ComplaintDraftResponse {
  return {
    id: "draft-empty",
    thread_id: "thread-empty",
    status: "DRAFT",
    created_by: "Demo User",
    complaint_source: null,
    customer_name: null,
    customer_contact: null,
    country_market: null,
    product_type: null,
    product_name: null,
    product_strength_grade: null,
    dosage_form: null,
    batch_lot_number: null,
    manufacturing_date: null,
    expiry_retest_date: null,
    quantity_affected: null,
    quantity_unit: null,
    complaint_type: null,
    complaint_date: null,
    detailed_description: null,
    defect_observed_date: null,
    sample_available: null,
    patient_consumed_product: null,
    adverse_event_signal: null,
    counterfeit_signal: null,
    storage_conditions: null,
    suggested_severity: null,
    suggested_priority: null,
    safety_route: null,
    risk_rationale: null,
    potential_hazard: null,
    suggested_next_action: null,
    risk_confidence: null,
    missing_fields: null,
    created_at: "2026-07-30T00:00:00Z",
    updated_at: "2026-07-30T00:00:00Z",
    is_locked: false,
    is_committed: false,
    is_extraction_active: false,
    ...overrides
  };
}

const emptyDraft = makeDraft();
const populatedDraft = makeDraft({
  id: "draft-populated",
  thread_id: "thread-populated",
  complaint_source: "Email-style complaint text",
  customer_name: "Demo Quality Contact",
  product_name: "Amoxicillin Capsules 500 mg",
  product_strength_grade: "500 mg",
  batch_lot_number: "BMX240602",
  manufacturing_date: "2024-06-02",
  expiry_retest_date: "2026-06-01",
  quantity_affected: "12.000",
  quantity_unit: "packs",
  complaint_type: "Capsule discolouration",
  complaint_date: "2026-07-30",
  detailed_description: "Customer reported visible colour variation in multiple capsules from one blister strip.",
  suggested_severity: "UNDETERMINED",
  suggested_priority: "UNDETERMINED"
});

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

function requestParts(input: RequestInfo | URL, init?: RequestInit) {
  if (input instanceof Request) {
    return { url: input.url, method: init?.method ?? input.method };
  }

  return { url: String(input), method: init?.method ?? "GET" };
}

function mockComplaintFetch(handler?: (request: { url: string; method: string }) => Response) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = requestParts(input, init);
    if (handler) {
      return handler(request);
    }

    if (request.url.endsWith("/complaint-drafts") && request.method === "POST") {
      return jsonResponse(emptyDraft, 201);
    }
    if (request.url.includes("/complaint-drafts/draft-empty/status")) {
      return jsonResponse({
        id: "draft-empty",
        status: "DRAFT",
        updated_at: emptyDraft.updated_at,
        is_locked: false,
        is_committed: false,
        is_extraction_active: false
      });
    }
    if (request.url.includes("/complaint-drafts/draft-empty")) {
      return jsonResponse(emptyDraft);
    }

    return jsonResponse({ detail: "Not found" }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderApp(preloadedState?: Partial<RootState>) {
  const store = createAppStore(preloadedState);
  render(
    <Provider store={store}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </Provider>
  );
  return store;
}

afterEach(() => {
  window.sessionStorage.clear();
  vi.unstubAllGlobals();
});

describe("App", () => {
  test("creates a draft when sessionStorage is empty", async () => {
    const fetchMock = mockComplaintFetch();

    renderApp();

    await waitFor(() => expect(window.sessionStorage.getItem("pharmaq_active_draft_id")).toBe("draft-empty"));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/complaint-drafts"),
      expect.objectContaining({ method: "POST" })
    );
  });

  test("restores a draft when sessionStorage has a valid ID", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-populated");
    const fetchMock = mockComplaintFetch((request) => {
      if (request.url.includes("/complaint-drafts/draft-populated/status")) {
        return jsonResponse({
          id: "draft-populated",
          status: "DRAFT",
          updated_at: populatedDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      if (request.url.includes("/complaint-drafts/draft-populated")) {
        return jsonResponse(populatedDraft);
      }
      return jsonResponse({ detail: "Unexpected request" }, 500);
    });

    renderApp();

    expect(await screen.findByDisplayValue("Amoxicillin Capsules 500 mg")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/complaint-drafts"),
      expect.objectContaining({ method: "POST" })
    );
  });

  test("replaces an invalid stored ID with a new draft", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "missing-draft");
    mockComplaintFetch((request) => {
      if (request.url.includes("/complaint-drafts/missing-draft")) {
        return jsonResponse({ detail: "ComplaintDraft not found" }, 404);
      }
      if (request.url.endsWith("/complaint-drafts") && request.method === "POST") {
        return jsonResponse(makeDraft({ id: "draft-replacement", thread_id: "thread-replacement" }), 201);
      }
      if (request.url.includes("/complaint-drafts/draft-replacement/status")) {
        return jsonResponse({
          id: "draft-replacement",
          status: "DRAFT",
          updated_at: emptyDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      if (request.url.includes("/complaint-drafts/draft-replacement")) {
        return jsonResponse(makeDraft({ id: "draft-replacement", thread_id: "thread-replacement" }));
      }
      return jsonResponse({ detail: "Unexpected request" }, 500);
    });

    renderApp();

    await waitFor(() => expect(window.sessionStorage.getItem("pharmaq_active_draft_id")).toBe("draft-replacement"));
    expect(screen.getByText("Saved complaint draft was unavailable, so a new draft was created.")).toBeInTheDocument();
  });

  test("existing fields populate from Redux", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-populated");
    mockComplaintFetch((request) => {
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-populated",
          status: "DRAFT",
          updated_at: populatedDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      return jsonResponse(populatedDraft);
    });

    renderApp();

    expect(await screen.findByDisplayValue("BMX240602")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Capsule discolouration")).toBeInTheDocument();
  });

  test("both locked workspace panels render in the required order", async () => {
    mockComplaintFetch();
    renderApp();

    const formPanel = await screen.findByTestId("complaint-form-panel");
    const assistantPanel = screen.getByTestId("complaint-assistant-panel");

    expect(screen.getByTestId("complaint-workspace")).toBeInTheDocument();
    expect(formPanel.compareDocumentPosition(assistantPanel)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  test("all required reference labels render", async () => {
    mockComplaintFetch();
    renderApp();

    for (const label of [
      "Log Customer Complaint",
      "API & FDF Quality Assurance Module",
      "Pending Triage",
      "ORIGIN & CUSTOMER DETAILS",
      "Complaint Source",
      "Customer Name",
      "PRODUCT & BATCH IDENTIFICATION",
      "Product Name",
      "Product Strength/Grade",
      "Batch/Lot Number",
      "Manufacturing Date",
      "Expiry Date",
      "Quantity Affected",
      "COMPLAINT DETAILS",
      "Complaint Type",
      "Complaint Date",
      "Detailed Complaint Description",
      "INITIAL ASSESSMENT & PRIORITY",
      "Initial Severity",
      "Priority",
      "Reset Form",
      "Save Complaint",
      "AI Complaint Intake Assistant",
      "BETA",
      "Drag & drop complaint document here",
      "or click to browse",
      "OR",
      "Paste Complaint Text / Email",
      "Supported formats: PDF, DOCX, TXT, EML",
      "Maximum file size: 10 MB",
      "EXTRACTION PROGRESS",
      "Ask me anything about this complaint...",
      "AI responses may contain errors. Please verify information."
    ]) {
      expect(await screen.findByText(label)).toBeInTheDocument();
    }
  });

  test("form remains read-only", async () => {
    mockComplaintFetch();
    renderApp();

    for (const label of [
      "Complaint Source",
      "Customer Name",
      "Product Name",
      "Product Strength/Grade",
      "Batch/Lot Number",
      "Manufacturing Date",
      "Expiry Date",
      "Quantity Affected",
      "Complaint Type",
      "Complaint Date",
      "Detailed Complaint Description",
      "Initial Severity",
      "Priority"
    ]) {
      expect(await screen.findByLabelText(label)).toHaveAttribute("readonly");
      expect(screen.getByLabelText(label)).toHaveAttribute("aria-readonly", "true");
    }
  });

  test("empty fields show awaiting AI extraction copy", async () => {
    mockComplaintFetch();
    renderApp();

    await waitFor(() => expect(screen.getAllByDisplayValue("Awaiting AI extraction...")).toHaveLength(13));
  });

  test("reset opens ConfirmationModal", async () => {
    mockComplaintFetch();
    const user = userEvent.setup();
    renderApp();

    await user.click(await screen.findByTestId("complaint-reset-button"));

    expect(screen.getByRole("dialog", { name: "Reset Complaint Draft" })).toBeInTheDocument();
    expect(screen.getByText(/Extracted complaint values will be cleared/i)).toBeInTheDocument();
  });

  test("reset keeps the same draft ID", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-populated");
    const resetDraft = makeDraft({ id: "draft-populated", thread_id: "thread-populated" });
    let currentDraft = populatedDraft;
    mockComplaintFetch((request) => {
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-populated",
          status: "DRAFT",
          updated_at: populatedDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      if (request.url.endsWith("/reset") && request.method === "POST") {
        currentDraft = resetDraft;
        return jsonResponse(resetDraft);
      }
      return jsonResponse(currentDraft);
    });
    const user = userEvent.setup();

    renderApp();

    await screen.findByDisplayValue("Amoxicillin Capsules 500 mg");
    await user.click(screen.getByTestId("complaint-reset-button"));
    await user.click(
      within(screen.getByRole("dialog", { name: "Reset Complaint Draft" })).getByRole("button", {
        name: "Reset Form"
      })
    );

    await waitFor(() => expect(window.sessionStorage.getItem("pharmaq_active_draft_id")).toBe("draft-populated"));
    await waitFor(() => expect(screen.getAllByDisplayValue("Awaiting AI extraction...")).toHaveLength(13));
  });

  test("failed fetch does not erase displayed state", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-populated");
    mockComplaintFetch((request) => {
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-populated",
          status: "DRAFT",
          updated_at: populatedDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      return jsonResponse({ detail: "Backend unavailable" }, 500);
    });

    renderApp({
      complaint: {
        activeDraftId: "draft-populated",
        complaintDraft: populatedDraft,
        draftStatus: null,
        isCreatingDraft: false,
        isLoadingDraft: false,
        isResettingDraft: false,
        draftError: null,
        draftInfoMessage: null,
        draftSuccessMessage: null,
        recentlyUpdatedFields: [],
        extractionStage: "idle",
        extractionProgress: 0,
        isComposerLocked: false,
        activeIntelligenceTab: "Batch Intelligence",
        isIntelligenceDockExpanded: false
      }
    });

    expect(screen.getByDisplayValue("Amoxicillin Capsules 500 mg")).toBeInTheDocument();
    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Amoxicillin Capsules 500 mg")).toBeInTheDocument();
  });

  test("save complaint remains in the existing footer", async () => {
    mockComplaintFetch();
    renderApp();

    const saveButton = await screen.findByTestId("complaint-save-button");
    expect(saveButton).toBeDisabled();
    expect(saveButton.closest("footer")).toHaveClass("complaint-footer-actions");
  });

  test("upload dropzone is keyboard accessible", async () => {
    const user = userEvent.setup();
    mockComplaintFetch();

    renderApp();

    const dropzone = await screen.findByTestId("complaint-upload-dropzone");
    dropzone.focus();
    expect(dropzone).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(dropzone).toBeEnabled();
  });

  test("assistant input is available", async () => {
    mockComplaintFetch();
    renderApp();

    expect(await screen.findByTestId("complaint-chat-input")).toBeEnabled();
    expect(screen.getByPlaceholderText("Ask me anything about this complaint...")).toBeInTheDocument();
  });

  test("quality intelligence dock remains below the workspace when draft data exists", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-populated");
    mockComplaintFetch((request) => {
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-populated",
          status: "DRAFT",
          updated_at: populatedDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      return jsonResponse(populatedDraft);
    });

    renderApp();

    await screen.findByDisplayValue("Amoxicillin Capsules 500 mg");
    const workspace = screen.getByTestId("complaint-workspace");
    const dock = screen.getByTestId("quality-intelligence-dock");

    expect(workspace.compareDocumentPosition(dock)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  test("no permanent third column exists", async () => {
    mockComplaintFetch();
    renderApp();

    const workspace = await screen.findByTestId("complaint-workspace");
    expect(workspace).toHaveAttribute("data-column-count", "2");
    expect(Array.from(workspace.children)).toHaveLength(2);
  });

  test("mobile responsive layout contract is marked", async () => {
    mockComplaintFetch();
    renderApp();

    expect(await screen.findByTestId("complaint-workspace")).toHaveAttribute("data-responsive", "stack-below-900");
  });

  test("Google Inter is configured on the workspace shell", async () => {
    mockComplaintFetch();
    renderApp();

    expect(await screen.findByLabelText("PharmaQ Sentinel complaint workspace")).toHaveAttribute(
      "data-font-family",
      "Inter"
    );
  });

  test("save complaint should not be enabled by populated data yet", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-populated");
    mockComplaintFetch((request) => {
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-populated",
          status: "DRAFT",
          updated_at: populatedDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      return jsonResponse(populatedDraft);
    });

    renderApp();

    await screen.findByDisplayValue("Amoxicillin Capsules 500 mg");
    const footer = within(screen.getByTestId("complaint-form-panel")).getByTestId("complaint-save-button");
    expect(footer).toBeDisabled();
  });
});
