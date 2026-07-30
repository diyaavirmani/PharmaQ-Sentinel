# Engineering Instructions for PharmaQ Sentinel

PharmaQ Sentinel is an AI-assisted pharmaceutical Customer Complaint Management System for API and Finished Dosage Form manufacturers. These instructions are mandatory for all coding agents working in this repository.

## Required Reading Before Editing

Before changing files, read:

- `docs/PRODUCT_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/UI_CONTRACT.md`
- `docs/DATA_INTEGRITY_RULES.md`
- `docs/AI_SAFETY_RULES.md`
- `docs/DECISIONS.md`
- This `AGENTS.md`

If these documents conflict with a task request, stop and ask for clarification unless the user explicitly updates the documentation.

## Work Discipline

- Inspect the existing code, tests, schemas, migrations, and styles before creating new abstractions.
- Implement only the requested feature or fix.
- Do not perform broad unrelated refactors while implementing one feature.
- Preserve backwards compatibility unless the task explicitly requires a breaking change.
- Prefer existing project patterns over introducing new frameworks or architectural styles.
- Read `docs/UI_CONTRACT.md` before editing any frontend file, component, route, style, or test.
- Keep frontend form fields for complaints read-only; changes must flow through the AI Complaint Intake Assistant.
- Preserve the locked two-panel Complaint Workspace contract for complaint intake, editing, and document extraction.
- Avoid placeholders, fake integrations, or UI states that pretend a feature works.
- Mark intentional future work with explicit `TODO:` comments that include the missing behavior and reason.
- Never commit credentials, API keys, tokens, `.env` files with secrets, private certificates, or exported production data.
- Do not store OpenAI API keys, database credentials, or other secrets in frontend code, build artifacts, source control, or browser-visible configuration.

## Testing and Verification

- Run relevant tests before reporting completion.
- If tests cannot be run, report exactly why.
- Add or update tests when behavior, data contracts, migrations, AI orchestration, audit logging, or API responses change.
- Verify that mutation paths create audit events with old value, new value, timestamp, actor, tool, reason, and actual model used.
- Verify that source evidence and uploaded documents are preserved unchanged.

## Reporting

When finishing a task, report:

- Files changed.
- Tests run and results.
- Any assumptions or limitations.
- Whether application behavior, schemas, migrations, or public APIs changed.

## Pharmaceutical and AI Safety Rules

- AI output is always a draft, recommendation, or suggestion until reviewed by authorized users.
- Never describe AI severity, root cause, CAPA, regulatory routing, or batch impact as a final authorized decision.
- Missing information must remain null or `Not provided`; do not invent complaint facts.
- Never silently overwrite complaint fields.
- Edit operations must use patch-and-merge semantics and preserve unrelated fields.
- Seeded mock pharmaceutical records are allowed, but the UI must not present them as real company records.
- The system must not claim to be FDA-approved, validated, certified, or 21 CFR Part 11 compliant.
