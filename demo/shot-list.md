# PharmaQ Sentinel Seven-Minute Demo Shot List

All demo data is fictional. The target final runtime is 6:50-7:10 at 1920x1080.

| Time | Route | Visible Action | Expected Result | Narration Cue | Fallback |
| --- | --- | --- | --- | --- | --- |
| 0:00 | `/` | Open landing page. Hover product title and CTA. | PharmaQ Sentinel landing page with launch action. | Product framing. | Open `/workspace` directly if landing route is unavailable. |
| 0:20 | `/workspace` | Click `Launch Complaint Workspace`. | Locked two-panel workspace appears. | Read-only controlled workspace. | Refresh once; report backend status if unavailable. |
| 0:35 | `/workspace` | Attempt to focus Product Name field, then type complaint in assistant composer. | Form remains read-only; assistant accepts natural-language complaint. | Facts enter through assistant. | Use same complaint text again if network timeout occurs. |
| 1:15 | `/workspace` | Wait for populated read-only fields and progress. | Product, batch, quantity, complaint type, severity and missing information are visible. | Draft recommendation and missing detail behavior. | Continue once any main fields are populated; document omitted fields in report. |
| 1:25 | `/workspace` | Click upload area and upload `demo/video-demo-complaint.pdf`. | File name and extraction progress appear. | Source document preservation. | Paste PDF text in composer only if upload fails; report fallback. |
| 2:05 | `/workspace` | Wait for document extraction and enriched fields. | Form remains same workspace; source-derived values appear. | Same draft is enriched, not replaced. | Continue if extraction returns safe error; report limitation. |
| 2:15 | `/workspace` | Type correction: complaint date is `2026-07-18`. | Complaint date updates while product, batch and quantity remain unchanged. | Patch-and-merge correction. | Retry once; do not use hidden development patch. |
| 2:55 | `/workspace` | Open evidence for Batch/Lot Number. | Overlay drawer opens without changing workspace columns. | Field evidence and auditability. | Open Evidence & Audit tab later if field drawer is unavailable. |
| 3:25 | `/workspace` | Open Quality Intelligence, run Batch Intelligence. | Batch impact panel, metrics and graph render below workspace. | Blast-radius decision support. | Keep tab visible with error message; report backend limitation. |
| 4:00 | `/workspace` | Click graph node/detail if available, then Simulate Scope and Run Simulation. | Overlay/detail and simulation result show simulation-only language. | No operational status changes. | Show simulation modal only; report if node click unavailable. |
| 4:25 | `/workspace` | Switch to Quality War Room and click Run War Room. | Specialist cards, auditor challenge and consensus appear. | Draft findings and challenge behavior. | Continue if deterministic mode is used; report mode. |
| 5:10 | `/workspace` | Type possible adverse-event update in assistant composer. | Safety wording and follow-up questions appear. | Human-reviewed PV route signal. | Use wording with "possible adverse event" to trigger route. |
| 5:45 | `/workspace` | Switch to Investigation Support, run support. | Duplicate table and playbook are visible. | Recurrence and investigation planning. | Continue with visible error and document limitation. |
| 6:20 | `/workspace` | Type summary request, click Save Complaint, acknowledge missing details if prompted, save. | Success banner and View QMS Ledger link appear. | Commit reviewed demo complaint. | If missing required values block save, report and skip ledger. |
| 6:40 | `/qms-ledger` | Open ledger, search `Amoxicillin`. | Saved complaint row with `BMX240602` is visible. | Ledger handoff. | Ledger search is product-name based; do not claim batch search. |
| 6:55 | `/workspace` | Return to workspace, open Evidence & Audit, preview/download/copy brief if enabled. | Inspector Replay and inspection brief actions appear. | Version snapshot and brief. | If committed state does not survive navigation, report limitation. |

## Recording Safeguards

- Use a clean Chromium context.
- Hide devtools, terminals, secrets and browser bookmarks.
- Use the visible assistant, upload area, buttons and overlays only.
- Do not call backend endpoints directly from the recording script to manipulate state.
- Do not modify Redux state, session storage beyond normal draft reset/creation, or MySQL data from the browser.
- Prefer deterministic demo mode only when live OpenAI is unavailable, and disclose that in `recording-report.md`.
