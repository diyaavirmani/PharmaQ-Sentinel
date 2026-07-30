# Data Integrity Rules

## Core Rules

1. Uploaded source documents must be preserved unchanged.
2. Derived text, OCR output, extracted fields, AI recommendations, and user corrections must be stored separately from original uploads.
3. Missing information must remain null or `Not provided`.
4. The AI must not invent product, batch, patient, reporter, event, market, or manufacturing details.
5. Complaint form fields must be read-only in the frontend.
6. Corrections must be submitted through the AI Complaint Intake Assistant.
7. Never silently overwrite complaint fields.
8. All edit operations must use patch-and-merge semantics.
9. Every mutation must create an audit event.
10. Immutable complaint versions must be preserved after meaningful mutations.
11. Seeded mock records must be identified as mock data.
12. Secrets must not be stored in source control.

## Patch-and-Merge Semantics

Patch-and-merge means a correction changes only the fields included in the accepted patch. Fields not included in the patch remain unchanged.

Patch application must:

- Validate field paths.
- Validate value types.
- Preserve unrelated fields.
- Preserve prior evidence unless the field value changes.
- Attach new evidence or correction references to changed fields.
- Create audit events for every changed field.
- Create a new immutable complaint version when complaint state changes.

Patch application must not:

- Replace the full complaint object when only a partial correction is intended.
- Delete unrelated values.
- Infer missing facts beyond the user's instruction or source evidence.
- Hide conflicts between existing values and proposed corrections.

## Audit Event Requirements

Every mutation must record:

- Entity type.
- Entity identifier.
- Field or JSON path changed.
- Old value.
- New value.
- Timestamp.
- Actor.
- Tool or subsystem.
- Reason.
- Actual model used when AI participated.
- Source evidence, document reference, or user instruction reference when applicable.

Audit events are append-only. Normal application features must not edit or delete audit events.

## Evidence Preservation

Every populated field should retain field-level source evidence when available.

Evidence may include:

- Source document identifier.
- Source file type.
- Source text span.
- OCR region.
- Email header or body reference.
- User correction message.
- Extraction tool.
- AI model used.
- Confidence.
- Timestamp.

If evidence is unavailable, store an explicit absence marker rather than fabricating evidence.

## Complaint Drafts, Versions, and Ledger Records

Complaint draft:

- The current working complaint state before commitment.
- Durable database state.
- Editable only through extraction workflows or assistant-mediated corrections.

Immutable complaint version:

- A historical representation of complaint state.
- Created after meaningful mutations.
- Never modified after creation.

Committed complaint record:

- A reviewed complaint state committed to the QMS ledger.
- Linked to draft history, immutable versions, audit events, source documents, and AI recommendations.
- Not a claim that the application is validated, certified, FDA-approved, or 21 CFR Part 11 compliant.

## Mock Data

Seeded mock pharmaceutical records are allowed for development and demonstrations.

Mock data must:

- Be labeled as mock, seeded, sample, or demonstration data.
- Avoid using real confidential company records.
- Never be presented in the UI as live or real company data.

## Secret Handling

- Do not commit API keys, tokens, database passwords, private certificates, or real credentials.
- Do not expose OpenAI API keys, database URLs, or MySQL credentials to the frontend.
- Use server-side environment variables or secret managers for provider keys.
- Keep example environment files free of real secrets.
