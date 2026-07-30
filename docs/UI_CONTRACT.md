# UI Contract

This document is a permanent product and engineering contract for the PharmaQ Sentinel user interface. Future frontend work must preserve this contract unless the user explicitly changes it.

## Locked Complaint Workspace

The supplied reference screenshot defines the primary Complaint Workspace. The core interface must remain a two-panel workspace:

```text
+---------------------------------------------------------------+
| Left: Log Customer Complaint | Right: AI Complaint Assistant   |
| Read-only structured form    | Upload, progress, and chat      |
+---------------------------------------------------------------+
```

The mandatory Log Complaint, Edit Complaint, and Document Extraction tools must operate inside this workspace. They must not open separate pages.

## Mandatory Stack

Frontend:

- React
- TypeScript
- Redux Toolkit
- React Redux
- Google Inter
- Custom CSS or CSS Modules
- No large UI component library

Backend:

- Python
- FastAPI

AI:

- LangGraph
- OpenAI API
- OpenAI API key must remain server-side

Database:

- MySQL 8 or newer

Do not introduce:

- Docker
- PostgreSQL
- Groq
- A large UI component library
- Tailwind unless the existing repository already uses it
- A second design system
- A separate chatbot page
- A separate document upload page

## Core UI Invariants

1. The complaint workspace must remain a two-column desktop layout.
2. The left panel must occupy approximately 58-60% of the workspace.
3. The right AI assistant panel must occupy approximately 40-42% of the workspace.
4. The left panel must appear before the assistant panel in the DOM.
5. The complaint form must remain read-only.
6. Users must enter and modify complaint information only through assistant chat, document upload, or pasted complaint text/email.
7. Mandatory tools must update the same Redux complaint draft.
8. Do not create separate forms for Log Complaint, Edit Complaint, or Document Extraction.
9. Do not rename labels shown in the reference UI without explicit instruction.
10. Do not remove existing fields to make room for new features.
11. Do not move risk assessment into a separate page.
12. Do not replace the assistant panel with an unrelated chatbot design.
13. Do not introduce a permanent third column.
14. Do not resize the left form when drawers or modals open.
15. Drawers must overlay the interface rather than shifting the layout.
16. Modals must overlay the interface rather than restructuring it.
17. Advanced features must appear below the locked two-column workspace in a collapsible Quality Intelligence Dock.
18. Advanced features must use tabs inside that dock: Batch Intelligence, Quality War Room, Evidence & Audit, and Investigation Support.
19. The Quality Intelligence Dock must remain hidden or collapsed when no complaint data is available.
20. The core complaint workspace must remain visible above the Quality Intelligence Dock.
21. The QMS Ledger may open as a full-width overlay or route using the same AppShell and design system. It must not change the Complaint Workspace layout.
22. Use the same Google Inter font, purple primary color, button style, input style, border style, status badge style, spacing scale, shadows, loading indicators, and disclaimer style.

## Reference UI Labels

Header labels:

- `Log Customer Complaint`
- `API & FDF Quality Assurance Module`
- `Pending Triage`

Origin and customer section:

- `ORIGIN & CUSTOMER DETAILS`
- `Complaint Source`
- `Customer Name`

Product and batch section:

- `PRODUCT & BATCH IDENTIFICATION`
- `Product Name`
- `Product Strength/Grade`
- `Batch/Lot Number`
- `Manufacturing Date`
- `Expiry Date`
- `Quantity Affected`

Complaint details section:

- `COMPLAINT DETAILS`
- `Complaint Type`
- `Complaint Date`
- `Detailed Complaint Description`

Initial assessment section:

- `INITIAL ASSESSMENT & PRIORITY`
- `Initial Severity`
- `Priority`

Left footer labels:

- `Reset Form`
- `Save Complaint`

Assistant panel labels:

- `AI Complaint Intake Assistant`
- `BETA`
- `Drag & drop complaint document here`
- `or click to browse`
- `Paste Complaint Text / Email`
- `Supported formats: PDF, DOCX, TXT, EML`
- `Maximum file size: 10 MB`
- `Extraction Progress`
- `Ask me anything about this complaint...`
- `AI responses may contain errors. Please verify information.`

## Component Contract

The application must maintain these components when the Complaint Workspace is implemented:

- `ComplaintWorkspace`
- `ComplaintFormPanel`
- `ComplaintAssistantPanel`
- `ReadOnlyField`
- `ComplaintSection`
- `UploadDropzone`
- `ExtractionProgress`
- `AssistantConversation`
- `AssistantComposer`
- `RiskAssessmentSection`
- `QualityIntelligenceDock`
- `OverlayDrawer`
- `ConfirmationModal`

Use stable test IDs:

- `complaint-workspace`
- `complaint-form-panel`
- `complaint-assistant-panel`
- `complaint-upload-dropzone`
- `complaint-extraction-progress`
- `complaint-chat-messages`
- `complaint-chat-input`
- `complaint-reset-button`
- `complaint-save-button`
- `quality-intelligence-dock`

## Feature Placement Rules

Log Complaint:

- User enters complaint text in the existing assistant composer.
- Assistant displays extraction progress.
- Left form populates in place.

Edit Complaint:

- User enters the correction in the same composer.
- Only changed fields briefly highlight.
- The structure of the form remains unchanged.

Document Extraction:

- User uses the existing assistant upload box.
- Progress appears in the existing Extraction Progress section.
- Extracted data populates the same form.

Completeness Checker:

- Display a compact card below Initial Assessment & Priority.
- Do not add another column.

Duplicate Detection:

- Display a compact alert below the complaint form.
- Detailed results belong inside Investigation Support.

Evidence:

- Display a small evidence icon inside or beside populated fields.
- Clicking the icon opens an overlay drawer.

Batch Blast-Radius:

- Display inside the Batch Intelligence tab in the lower Quality Intelligence Dock.

Quality War Room:

- Display inside the Quality War Room tab in the lower Quality Intelligence Dock.

Audit Timeline:

- Display inside Evidence & Audit.

Inspection Brief:

- Display preview and export actions inside Evidence & Audit.

Root Cause and CAPA suggestions:

- Display inside Investigation Support.
- Do not place long recommendation lists directly inside the core form.

## Responsive Rules

At widths below approximately 900px:

- Stack the form above the assistant.
- Keep the form read-only.
- Keep assistant upload and chat controls usable.
- Place the Quality Intelligence Dock below both panels.
- Avoid horizontal scrolling.

## Regression Protection

Before changing frontend code:

1. Inspect the current Complaint Workspace.
2. Identify whether the change can be implemented without modifying its structure.
3. Reuse existing components and tokens.
4. Avoid broad CSS refactors.
5. Avoid changing global selectors unnecessarily.

After every frontend feature:

1. Run TypeScript checks.
2. Run frontend tests.
3. Run production build.
4. Run layout contract tests.
5. Run Playwright screenshots for empty workspace, populated workspace, document extraction state, edit-highlight state, and mobile stacked state.

Screenshot and layout contract tests must ensure:

- Left and right panels still exist.
- Panel order has not changed.
- Width proportions remain approximately correct.
- Core labels remain visible.
- No permanent third column exists.
- Advanced content remains below the main workspace.
- Form fields remain read-only.

## Design System Continuity

The Complaint Workspace must use the existing design tokens and visual language. Future features should use the same primary purple, typography, spacing, borders, shadows, button treatment, status badges, loading indicators, and disclaimer styling.
