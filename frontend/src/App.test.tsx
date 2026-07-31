import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { afterEach, describe, expect, test, vi } from "vitest";
import { App } from "./App";
import { createAppStore, type RootState } from "./app/store";
import type { ComplaintDraftResponse, ComplaintResponse } from "./features/complaint/complaintTypes";

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
    manufacturing_date_text: null,
    expiry_retest_date: null,
    expiry_retest_date_text: null,
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

const riskDraft = makeDraft({
  id: "draft-risk",
  thread_id: "thread-risk",
  product_name: "Amoxicillin Capsules 500 mg",
  product_strength_grade: "500 mg",
  batch_lot_number: "BMX240602",
  complaint_type: "Capsule discolouration",
  detailed_description: "Customer reported visible colour variation in capsules.",
  suggested_severity: "MAJOR",
  suggested_priority: "HIGH",
  safety_route: "PRODUCT_QUALITY",
  risk_rationale: "Visible capsule discolouration may indicate a product quality issue requiring QA review.",
  potential_hazard: "Potential product quality impact cannot be excluded.",
  suggested_next_action: "Request sample return and patient consumption details.",
  risk_confidence: "0.6200",
  missing_fields: {
    completeness: {
      completeness_percentage: 72,
      can_begin_triage: true,
      missing_critical_fields: [],
      missing_recommended_fields: ["sample availability", "patient consumption status"],
      targeted_follow_up_questions: [
        "Is a sample of the affected product available for return and laboratory inspection?",
        "Did any patient consume or use the product before the issue was noticed?"
      ],
      blockers: [],
      warnings: []
    },
    risk: {
      route_chips: ["QUALITY_ASSURANCE"],
      one_line_rationale: "Visible capsule discolouration may indicate a product quality issue requiring QA review.",
      potential_hazards: ["Potential product quality impact cannot be excluded."],
      supporting_evidence: ["possible degradation from discolouration: discoloured"],
      contradicting_evidence: [],
      recommended_actions: ["Request sample return and patient consumption details."],
      limitations: ["Draft recommendation requiring authorised QA review."],
      requires_qa_confirmation: true,
      critical_signals: []
    }
  }
});

const evidenceListResponse = {
  items: [
    {
      id: "evidence-product",
      draft_id: "draft-risk",
      field_name: "product_name",
      field_value: { value: "Amoxicillin Capsules 500 mg" },
      display_value: "Amoxicillin Capsules 500 mg",
      evidence_type: "USER_TEXT",
      evidence_status: "EXPLICIT_SOURCE",
      conflict_status: "NONE",
      active_reason: "currently active source evidence",
      source_message_id: "msg-source",
      source_attachment_id: null,
      source_message: {
        id: "msg-source",
        role: "USER",
        message_text: "Apollo Pharmacy reported Amoxicillin Capsules 500 mg.",
        created_at: "2026-07-30T00:00:00Z"
      },
      source_attachment: null,
      page_number: null,
      paragraph_index: null,
      source_excerpt: "Apollo Pharmacy reported Amoxicillin Capsules 500 mg.",
      confidence: "0.9100",
      extraction_method: "LOG_COMPLAINT",
      is_explicit: true,
      is_normalised: false,
      is_inferred: false,
      is_active: true,
      provider_name: "openai",
      actual_model: "mock-model",
      created_at: "2026-07-30T00:00:01Z"
    }
  ],
  limit: 200,
  offset: 0,
  next_offset: null,
  conflicts: [],
  critical_conflicts_block_save: false
};

const evidenceDetailResponse = {
  field_name: "product_name",
  current_value: "Amoxicillin Capsules 500 mg",
  current_active_evidence: evidenceListResponse.items[0],
  evidence_history: evidenceListResponse.items,
  conflicts: [],
  critical_conflict_unresolved: false
};

const timelineResponse = {
  items: [
    {
      event_id: "evt-field",
      event_type: "LOG_COMPLAINT_FIELD_CHANGED",
      actor: "AI_AGENT",
      timestamp: "2026-07-30T00:00:01Z",
      title: "Field populated",
      description: "product_name was populated from source evidence.",
      affected_fields: ["product_name"],
      old_value: { value: null },
      new_value: { value: "Amoxicillin Capsules 500 mg" },
      evidence_references: ["evidence-product"],
      attachment_references: [],
      provider_name: "openai",
      actual_model: "mock-model"
    }
  ],
  limit: 200,
  offset: 0,
  next_offset: null
};

const committedComplaint: ComplaintResponse = {
  id: "complaint-ledger-1",
  complaint_number: "PQC-2026-000001",
  current_version_number: 1,
  status: "COMMITTED",
  committed_from_draft_id: "draft-risk",
  committed_at: "2026-07-31T00:00:00Z",
  committed_by: "Demo QA User",
  review_meaning: "I reviewed the complaint information and AI-suggested assessment.",
  missing_information_acknowledged: true,
  unresolved_missing_information: riskDraft.missing_fields,
  latest_risk_assessment_id: "risk-version-1",
  complaint_source: riskDraft.complaint_source,
  customer_name: riskDraft.customer_name,
  customer_contact: riskDraft.customer_contact,
  country_market: riskDraft.country_market,
  product_type: riskDraft.product_type,
  product_name: riskDraft.product_name,
  product_strength_grade: riskDraft.product_strength_grade,
  dosage_form: riskDraft.dosage_form,
  batch_lot_number: riskDraft.batch_lot_number,
  manufacturing_date: riskDraft.manufacturing_date,
  manufacturing_date_text: riskDraft.manufacturing_date_text,
  expiry_retest_date: riskDraft.expiry_retest_date,
  expiry_retest_date_text: riskDraft.expiry_retest_date_text,
  quantity_affected: riskDraft.quantity_affected,
  quantity_unit: riskDraft.quantity_unit,
  complaint_type: riskDraft.complaint_type,
  complaint_date: riskDraft.complaint_date,
  detailed_description: riskDraft.detailed_description,
  defect_observed_date: riskDraft.defect_observed_date,
  sample_available: riskDraft.sample_available,
  patient_consumed_product: riskDraft.patient_consumed_product,
  adverse_event_signal: riskDraft.adverse_event_signal,
  counterfeit_signal: riskDraft.counterfeit_signal,
  storage_conditions: riskDraft.storage_conditions,
  suggested_severity: riskDraft.suggested_severity,
  suggested_priority: riskDraft.suggested_priority,
  safety_route: riskDraft.safety_route,
  risk_rationale: riskDraft.risk_rationale,
  potential_hazard: riskDraft.potential_hazard,
  suggested_next_action: riskDraft.suggested_next_action,
  risk_confidence: riskDraft.risk_confidence,
  missing_fields: riskDraft.missing_fields,
  created_at: "2026-07-31T00:00:00Z",
  updated_at: "2026-07-31T00:00:00Z"
};

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
  const persistedMessages = [
    {
      id: "msg-user",
      draft_id: "draft-empty",
      role: "USER",
      message_text: "What information is missing?",
      attachment_id: null,
      created_at: "2026-07-30T00:00:00Z",
      metadata_json: null
    },
    {
      id: "msg-assistant",
      draft_id: "draft-empty",
      role: "ASSISTANT",
      message_text: "Currently missing: Product Name.",
      attachment_id: null,
      created_at: "2026-07-30T00:00:01Z",
      metadata_json: null
    }
  ];
  let messageStore: typeof persistedMessages = [];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = requestParts(input, init);
    if (!request.url.endsWith("/messages") && handler) {
      return handler(request);
    }

    if (request.url.endsWith("/messages") && request.method === "GET") {
      return jsonResponse({ messages: messageStore, limit: 50, offset: 0, next_offset: null });
    }
    if (request.url.endsWith("/messages") && request.method === "POST") {
      messageStore = persistedMessages;
      return jsonResponse({
        user_message: persistedMessages[0],
        assistant_message: persistedMessages[1],
        intent: "ASK_QUESTION",
        tool_name: null,
        draft: emptyDraft,
        changed_fields: [],
        warnings: [],
        clarification_required: false
      });
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
        isSavingComplaint: false,
        draftError: null,
        draftInfoMessage: null,
        draftSuccessMessage: null,
        recentlyUpdatedFields: [],
        extractionStage: "idle",
        extractionProgress: 0,
        isComposerLocked: false,
        assistantMessages: [],
        isSendingMessage: false,
        activeAttachmentId: null,
        selectedUploadFilename: null,
        uploadError: null,
        hasCriticalEvidenceConflict: false,
        committedComplaint: null,
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

  test("save complaint opens review modal and saves from existing footer", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-risk");
    let isSaved = false;
    const fetchMock = mockComplaintFetch((request) => {
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-risk",
          status: isSaved ? "COMMITTED" : "DRAFT",
          updated_at: riskDraft.updated_at,
          is_locked: isSaved,
          is_committed: isSaved,
          is_extraction_active: false
        });
      }
      if (request.url.includes("/evidence")) {
        return jsonResponse(evidenceListResponse);
      }
      if (request.url.includes("/timeline")) {
        return jsonResponse(timelineResponse);
      }
      if (request.url.endsWith("/save") && request.method === "POST") {
        isSaved = true;
        return jsonResponse(committedComplaint);
      }
      if (request.url.includes("/complaint-drafts/draft-risk")) {
        return jsonResponse(
          isSaved
            ? {
                ...riskDraft,
                status: "COMMITTED",
                is_locked: true,
                is_committed: true,
                updated_at: committedComplaint.updated_at
              }
            : riskDraft
        );
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });
    const user = userEvent.setup();

    renderApp();

    await screen.findByDisplayValue("Amoxicillin Capsules 500 mg");
    const saveButton = screen.getByTestId("complaint-save-button");
    expect(saveButton.closest("footer")).toHaveClass("complaint-footer-actions");
    expect(saveButton).toBeEnabled();

    await user.click(saveButton);
    const dialog = screen.getByRole("dialog", { name: "Save Complaint" });
    expect(within(dialog).getByText("Suggested Severity")).toBeInTheDocument();
    expect(within(dialog).getByText("sample availability")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Save Complaint" })).toBeDisabled();

    await user.click(within(dialog).getByLabelText("I acknowledge the listed non-critical missing information."));
    await user.click(within(dialog).getByRole("button", { name: "Save Complaint" }));

    expect(await screen.findByText(/PQC-2026-000001 saved to the demonstration QMS ledger/)).toBeInTheDocument();
    expect(await screen.findByText("Committed")).toBeInTheDocument();
    expect(screen.getByText("View QMS Ledger")).toBeInTheDocument();
    expect(screen.getByTestId("complaint-chat-input")).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/complaint-drafts/draft-risk/save"), expect.anything());
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

  test("upload uses existing dropzone and populates the same form", async () => {
    const user = userEvent.setup();
    let uploaded = false;
    mockComplaintFetch((request) => {
      if (request.url.includes("/attachments/attachment-demo/status")) {
        return jsonResponse({
          attachment_id: "attachment-demo",
          original_filename: "complaint.txt",
          status: "COMPLETE",
          progress_percentage: 100,
          current_stage: "COMPLETE",
          safe_error: null,
          created_at: "2026-07-30T00:00:00Z",
          completed_at: "2026-07-30T00:00:01Z"
        });
      }
      if (request.url.endsWith("/attachments") && request.method === "POST") {
        uploaded = true;
        return jsonResponse({
          attachment_id: "attachment-demo",
          original_filename: "complaint.txt",
          status: "COMPLETE",
          progress_percentage: 100,
          current_stage: "COMPLETE",
          duplicate: false,
          changed_fields: ["product_name", "batch_lot_number"],
          created_at: "2026-07-30T00:00:00Z"
        });
      }
      if (request.url.endsWith("/complaint-drafts") && request.method === "POST") {
        return jsonResponse(emptyDraft, 201);
      }
      if (request.url.includes("/complaint-drafts/draft-empty/status")) {
        return jsonResponse({
          id: "draft-empty",
          status: "DRAFT",
          updated_at: populatedDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      if (request.url.includes("/complaint-drafts/draft-empty")) {
        return jsonResponse(uploaded ? populatedDraft : emptyDraft);
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });
    renderApp();

    await screen.findByTestId("complaint-upload-dropzone");
    const fileInput = document.querySelector<HTMLInputElement>(".upload-dropzone__input");
    expect(fileInput).not.toBeNull();
    await user.upload(
      fileInput as HTMLInputElement,
      new File(["Apollo Pharmacy reported batch BMX240602."], "complaint.txt", { type: "text/plain" })
    );

    expect(await screen.findByText("complaint.txt")).toBeInTheDocument();
    expect(await screen.findByDisplayValue("Amoxicillin Capsules 500 mg")).toBeInTheDocument();
    expect(screen.getByTestId("complaint-extraction-progress")).toHaveTextContent("100%");
    expect(screen.getByTestId("complaint-workspace").children).toHaveLength(2);
  });

  test("assistant input is available", async () => {
    mockComplaintFetch();
    renderApp();

    expect(await screen.findByTestId("complaint-chat-input")).toBeEnabled();
    expect(screen.getByPlaceholderText("Ask me anything about this complaint...")).toBeInTheDocument();
  });

  test("same composer handles assistant messages", async () => {
    const fetchMock = mockComplaintFetch();
    const user = userEvent.setup();
    renderApp();

    const input = await screen.findByTestId("complaint-chat-input");
    await user.type(input, "What information is missing?");
    await user.click(screen.getByRole("button", { name: "Send assistant message" }));

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/complaint-drafts/draft-empty/messages"),
      expect.objectContaining({ method: "POST" })
    );
    expect(await screen.findByText("Currently missing: Product Name.")).toBeInTheDocument();
    expect(screen.getAllByTestId("complaint-chat-input")).toHaveLength(1);
  });

  test("risk details and completeness remain inside existing section four", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-risk");
    const fetchMock = mockComplaintFetch((request) => {
      if (request.url.includes("/messages") && request.method === "POST") {
        return jsonResponse({
          user_message: {
            id: "msg-risk-follow-up-user",
            draft_id: "draft-risk",
            role: "USER",
            message_text: "Please ask these follow-up questions.",
            attachment_id: null,
            created_at: "2026-07-30T00:00:00Z",
            metadata_json: null
          },
          assistant_message: {
            id: "msg-risk-follow-up-assistant",
            draft_id: "draft-risk",
            role: "ASSISTANT",
            message_text: "Please confirm sample availability and patient consumption status.",
            attachment_id: null,
            created_at: "2026-07-30T00:00:01Z",
            metadata_json: null
          },
          intent: "ASK_QUESTION",
          tool_name: null,
          draft: riskDraft,
          changed_fields: [],
          warnings: [],
          clarification_required: false
        });
      }
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-risk",
          status: "DRAFT",
          updated_at: riskDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      return jsonResponse(riskDraft);
    });
    const user = userEvent.setup();
    renderApp();

    const riskDetailsCard = await screen.findByTestId("risk-details-card");
    const sectionFour = screen.getByRole("heading", { name: "INITIAL ASSESSMENT & PRIORITY" });
    expect(sectionFour.closest(".complaint-section")).toContainElement(riskDetailsCard);
    expect(screen.getByText("Quality Assurance")).toBeInTheDocument();
    expect(screen.getByText("Requires QA confirmation")).toBeInTheDocument();
    expect(screen.getByTestId("completeness-card")).toHaveTextContent("72% complete");

    await user.click(screen.getByRole("button", { name: "Ask follow-up questions" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/complaint-drafts/draft-risk/messages"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("sample of the affected product")
        })
      )
    );
    expect(screen.getByTestId("complaint-workspace").children).toHaveLength(2);
  });

  test("evidence icon opens overlay drawer without changing field order", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-risk");
    mockComplaintFetch((request) => {
      if (request.url.includes("/evidence/product_name")) {
        return jsonResponse(evidenceDetailResponse);
      }
      if (request.url.includes("/evidence")) {
        return jsonResponse(evidenceListResponse);
      }
      if (request.url.includes("/timeline")) {
        return jsonResponse(timelineResponse);
      }
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-risk",
          status: "DRAFT",
          updated_at: riskDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      return jsonResponse(riskDraft);
    });
    const user = userEvent.setup();
    renderApp();

    const productName = await screen.findByLabelText("Product Name");
    const strength = screen.getByLabelText("Product Strength/Grade");
    expect(productName.compareDocumentPosition(strength)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);

    await user.click(await screen.findByRole("button", { name: "View evidence for Product Name" }));

    expect(await screen.findByRole("dialog", { name: "Evidence: Product Name" })).toBeInTheDocument();
    expect(screen.getAllByText("Apollo Pharmacy reported Amoxicillin Capsules 500 mg.").length).toBeGreaterThan(0);
    expect(screen.getByTestId("complaint-workspace").children).toHaveLength(2);
    expect(document.querySelector(".overlay-backdrop")).toBeInTheDocument();
  });

  test("inspector replay stays inside Evidence and Audit dock tab", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-risk");
    mockComplaintFetch((request) => {
      if (request.url.includes("/evidence")) {
        return jsonResponse(evidenceListResponse);
      }
      if (request.url.includes("/timeline")) {
        return jsonResponse(timelineResponse);
      }
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-risk",
          status: "DRAFT",
          updated_at: riskDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      return jsonResponse(riskDraft);
    });
    const user = userEvent.setup();
    renderApp();

    await screen.findByDisplayValue("Amoxicillin Capsules 500 mg");
    await user.click(screen.getByRole("button", { name: "Quality Intelligence" }));
    await user.click(screen.getByRole("tab", { name: "Evidence & Audit" }));

    expect(screen.getByTestId("inspector-replay")).toBeInTheDocument();
    expect(screen.getByText("Field populated")).toBeInTheDocument();
    expect(screen.getByLabelText("Inspector Replay filters")).toBeInTheDocument();
    expect(screen.getByTestId("quality-intelligence-dock").compareDocumentPosition(screen.getByTestId("complaint-workspace"))).toBe(Node.DOCUMENT_POSITION_PRECEDING);
    expect(screen.getByTestId("complaint-workspace").children).toHaveLength(2);
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

  test("qms ledger route displays search filters and saved complaint table", async () => {
    window.history.pushState({}, "", "/qms-ledger");
    mockComplaintFetch((request) => {
      if (request.url.includes("/complaints")) {
        return jsonResponse({
          items: [committedComplaint],
          limit: 10,
          offset: 0,
          next_offset: null
        });
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });

    renderApp();

    expect(await screen.findByRole("heading", { name: "Saved Complaints" })).toBeInTheDocument();
    expect(screen.getByLabelText("Search")).toBeInTheDocument();
    expect(await screen.findByText("PQC-2026-000001")).toBeInTheDocument();
    expect(screen.getByText("Amoxicillin Capsules 500 mg")).toBeInTheDocument();
    expect(screen.getByText("BMX240602")).toBeInTheDocument();
  });

  test("workspace restores after ledger navigation without creating a new draft", async () => {
    window.sessionStorage.setItem("pharmaq_active_draft_id", "draft-risk");
    window.history.pushState({}, "", "/qms-ledger");
    const fetchMock = mockComplaintFetch((request) => {
      if (request.url.includes("/complaints")) {
        return jsonResponse({ items: [committedComplaint], limit: 10, offset: 0, next_offset: null });
      }
      if (request.url.includes("/status")) {
        return jsonResponse({
          id: "draft-risk",
          status: "DRAFT",
          updated_at: riskDraft.updated_at,
          is_locked: false,
          is_committed: false,
          is_extraction_active: false
        });
      }
      if (request.url.includes("/evidence")) {
        return jsonResponse(evidenceListResponse);
      }
      if (request.url.includes("/timeline")) {
        return jsonResponse(timelineResponse);
      }
      if (request.url.includes("/complaint-drafts/draft-risk")) {
        return jsonResponse(riskDraft);
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });
    const user = userEvent.setup();

    renderApp();
    await user.click(await screen.findByRole("link", { name: "Complaint Workspace" }));

    expect(await screen.findByDisplayValue("Amoxicillin Capsules 500 mg")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/complaint-drafts"),
      expect.objectContaining({ method: "POST" })
    );
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
