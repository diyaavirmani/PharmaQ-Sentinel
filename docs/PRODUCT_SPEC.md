# PharmaQ Sentinel Product Specification

## Purpose

PharmaQ Sentinel is an AI-assisted pharmaceutical Customer Complaint Management System for Active Pharmaceutical Ingredient (API) and Finished Dosage Form (FDF) manufacturers.

The product accepts complaints through natural-language text, email-style text, PDF, DOCX, EML, and image uploads. Users must not manually enter or edit complaint form fields. All complaint form population and correction must happen through the AI Complaint Intake Assistant.

The system supports complaint intake, structured extraction, evidence review, missing information detection, AI-suggested risk assessment, auditability, QMS ledger commitment, batch blast-radius analysis, and an AI Quality War Room.

The primary complaint interface is the locked Complaint Workspace defined in `docs/UI_CONTRACT.md`.

## Core Product Principles

- Complaint data must be traceable to user input, source documents, or explicit natural-language corrections.
- AI-generated content must remain reviewable and must never be represented as an authorized quality decision.
- Human reviewers remain responsible for accepting, rejecting, or committing complaint records.
- Data integrity, evidence preservation, and auditability are product features, not implementation details.
- The application must support both API and FDF complaint workflows.

## Mandatory Capabilities

1. Accept complaint intake from natural-language text, email-style text, PDF, DOCX, EML, and image uploads.
2. Extract structured pharmaceutical complaint data.
3. Populate a read-only complaint form.
4. Allow natural-language corrections through the AI Complaint Intake Assistant.
5. Preserve unrelated fields during correction.
6. Generate an initial AI-suggested risk assessment.
7. Detect missing complaint details.
8. Preserve field-level source evidence.
9. Maintain a complete audit trail.
10. Commit reviewed complaints into a QMS ledger.
11. Provide a Batch Blast-Radius Digital Twin.
12. Provide an AI Quality War Room.

## Complaint Intake

Supported input types:

- Plain natural-language complaint text.
- Email-style pasted text.
- PDF uploads.
- DOCX uploads.
- EML uploads.
- Image uploads requiring OCR or visual extraction.

Uploaded source documents must be preserved unchanged. Derived text, OCR output, extracted entities, and AI analysis must be stored separately from the original upload.

## Complaint Form Behavior

Complaint form fields are read-only in the UI.

Users may correct or supplement complaint information only by instructing the AI Complaint Intake Assistant in natural language. For example, a user may say: "The batch number is B-1042, not B-1041, and the dosage form was tablet."

Log Complaint, Edit Complaint, and Document Extraction must use the same two-panel Complaint Workspace. The read-only structured form remains on the left, the AI Complaint Intake Assistant remains on the right, and both panels update the same complaint draft state. These workflows must not be split into separate pages or alternate form layouts.

The assistant must convert the instruction into a proposed patch. Patch application must:

- Update only fields addressed by the user or safely inferred from the instruction.
- Preserve unrelated existing fields.
- Record old value and new value for each mutation.
- Link the correction to the user instruction as evidence.
- Create an audit event.
- Preserve previous immutable complaint versions.

## Structured Complaint Data

The data model must support API and FDF complaints. Exact schemas may evolve, but complaint drafts and committed records should cover these categories:

- Complaint identifiers and lifecycle status.
- Complainant and reporter details when provided.
- Product type: API or FDF.
- Product name and material identifiers.
- Batch, lot, manufacturing, and expiry details when provided.
- Dosage form, strength, pack, route, or API grade as applicable.
- Complaint description.
- Defect category and defect details.
- Date received and event dates when provided.
- Market, customer, site, supplier, and distribution context when provided.
- Suspected quality impact.
- Adverse event or medical relevance indicators when provided.
- Attachments and source evidence.
- Missing information list.
- AI-suggested risk assessment.
- Human review and QMS ledger commitment metadata.

Missing information must remain null or `Not provided`. The AI must not invent complaint facts.

## AI-Suggested Risk Assessment

The system may generate an initial AI-suggested risk assessment. This assessment must be clearly labeled as AI-generated and not final.

Each recommendation must include:

- Recommendation type.
- Evidence used.
- Confidence.
- Limitations.
- Actual model used.
- Timestamp.

AI recommendations may include suggested severity, triage priority, possible investigation focus, possible root-cause hypotheses, possible CAPA considerations, possible regulatory routing indicators, missing detail prompts, and batch impact signals. These must never be presented as final authorized decisions.

## Missing Information Detection

The system must identify missing complaint details needed for review. Missing fields should remain visible as null or `Not provided`, with prompts that help users provide corrections through the assistant.

The assistant may ask clarifying questions, but it must not manufacture missing values.

## Field-Level Evidence

Each populated field should preserve source evidence whenever available:

- Source document identifier.
- Source type.
- Extracted text span, OCR region, email header, or user correction reference.
- Confidence.
- Extraction timestamp.
- Actual model or tool used.

When evidence is unavailable, the system should mark the field as lacking evidence instead of pretending evidence exists.

## QMS Ledger

Reviewed complaint drafts can be committed into a QMS ledger. A committed complaint record represents a reviewed state accepted for downstream quality workflows.

Commitment must:

- Preserve the committed complaint record.
- Link to immutable complaint versions.
- Preserve the full audit history.
- Identify the actor and timestamp.
- Record that AI recommendations were draft inputs, not final authority.

## Batch Blast-Radius Digital Twin

The Batch Blast-Radius Digital Twin evaluates possible batch impact using complaint data and seeded or configured pharmaceutical records. It may analyze relationships such as:

- Same batch or lot.
- Same product or material.
- Same manufacturing site or line.
- Same supplier or component.
- Same time window.
- Similar defect pattern.
- Distribution exposure.
- Related deviations, stability signals, or prior complaints when available.

Seeded mock pharmaceutical records are allowed for development and demonstrations, but the UI must clearly identify mock data and must not pretend it is real company data.

Batch Blast-Radius output belongs inside the Batch Intelligence tab of the Quality Intelligence Dock below the core Complaint Workspace.

## AI Quality War Room

The AI Quality War Room supports collaborative, evidence-grounded complaint review. It should provide:

- Complaint summary.
- Open missing information.
- AI recommendations with evidence, confidence, and limitations.
- Batch impact view.
- Timeline and audit trail.
- Discussion or action tracking when implemented.
- Clear separation between AI suggestions and authorized human decisions.

The Quality War Room belongs inside the Quality War Room tab of the Quality Intelligence Dock below the core Complaint Workspace. It must not replace the assistant panel or move the risk assessment out of the form area.

## UI Layout Contract

The core Complaint Workspace must preserve the reference UI labels, component names, test IDs, layout proportions, responsive behavior, and regression checks listed in `docs/UI_CONTRACT.md`.

At desktop widths, the workspace remains two columns: approximately 58-60% read-only form on the left and 40-42% AI assistant on the right. Below approximately 900px, the form stacks above the assistant. Advanced features appear below both panels in the Quality Intelligence Dock.

## Out of Scope Unless Explicitly Requested

- Claiming regulatory validation, FDA approval, certification, or 21 CFR Part 11 compliance.
- Manual editing of complaint fields.
- Frontend exposure of AI provider credentials.
- Production QMS integrations without explicit design and validation requirements.
