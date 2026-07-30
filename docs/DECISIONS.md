# Architecture Decisions

This file records durable engineering decisions for PharmaQ Sentinel. Add new decisions as dated entries. Do not remove old decisions unless they are explicitly superseded.

## 2026-07-30: Documentation-First Repository Baseline

Decision:

Create permanent engineering, product, architecture, data integrity, and AI safety documentation before scaffolding application code.

Rationale:

PharmaQ Sentinel handles pharmaceutical complaint workflows where auditability, source evidence, AI limitations, and data integrity must shape implementation from the first commit.

Implications:

- Future agents must read the documentation before editing.
- Application code should conform to these constraints.
- Scaffolding is intentionally deferred.

## 2026-07-30: Mandatory Full-Stack Architecture

Decision:

Superseded by the later 2026-07-30 MySQL/OpenAI local scaffold decision below.

Rationale:

The stack is explicit assignment scope and supports a typed frontend, a Python API, durable relational data, and migration-controlled schema evolution.

Implications:

- Frontend scaffolding must use the mandated libraries.
- Backend scaffolding must use the mandated Python stack.
- UI implementation should build focused components rather than importing a broad component framework.

## 2026-07-30: Backend-Only AI Provider Access

Decision:

Superseded by the later 2026-07-30 OpenAI server-side provider decision below.

Rationale:

Provider secrets must remain server-side, and every AI operation needs consistent model validation, fallback behavior, metadata capture, and audit integration.

Implications:

- Superseded: frontend code must call backend API endpoints and never call an LLM provider directly.
- Server-side configuration controls model selection.
- The actual model used must be recorded for AI outputs and AI-assisted mutations.

## 2026-07-30: Superseded Earlier Model Selection

Decision:

Superseded by the later 2026-07-30 OpenAI environment-driven model decision below.

Rationale:

Model availability can change, and the application must behave predictably while satisfying assignment requirements.

Implications:

- Startup or first-use validation should check available models.
- Unsupported configured models must fail clearly or fall back according to policy.
- Audit metadata must record the actual model used.

## 2026-07-30: Read-Only Complaint Form

Decision:

Complaint form fields in the UI are read-only. Users correct fields only through natural-language instructions to the AI Complaint Intake Assistant.

Rationale:

This keeps the product centered on AI-assisted intake while preserving auditability and traceability for changes.

Implications:

- UI components must not expose direct field editors for complaint form fields.
- Corrections must be interpreted as patches.
- Every accepted correction must produce audit events and complaint versions.

## 2026-07-30: Patch-and-Merge for Corrections

Decision:

All edit operations must use patch-and-merge semantics. Full-object replacement is not acceptable for partial corrections.

Rationale:

Complaint data can be partially extracted from many sources. Corrections must not delete unrelated fields or evidence.

Implications:

- Patch validators must reject unknown field paths and malformed values.
- Application services must preserve unrelated fields.
- Old value and new value must be audited per changed field.

## 2026-07-30: Separate AI Orchestration State from Durable Complaint State

Decision:

LangGraph conversation state, complaint draft database state, committed complaint records, immutable complaint versions, and audit events are separate concepts.

Rationale:

AI orchestration needs flexible workflow context, while complaint records require durable, auditable, versioned database state.

Implications:

- LangGraph state must not be the source of truth for complaints.
- Database services own durable complaint mutation.
- Audit events and immutable versions both remain necessary.

## 2026-07-30: AI Recommendations Are Not Final Decisions

Decision:

AI severity, root cause, CAPA, regulatory routing, missing information analysis, and batch impact outputs must be presented as recommendations or drafts with evidence, confidence, limitations, and actual model used.

Rationale:

The system assists pharmaceutical quality review but does not replace authorized decision-makers.

Implications:

- UI copy must avoid final-authority language.
- API schemas should represent recommendation metadata explicitly.
- Tests should check that recommendations include required metadata.

## 2026-07-30: No Regulatory Compliance Claims

Decision:

The system must not claim to be FDA-approved, validated, certified, or 21 CFR Part 11 compliant.

Rationale:

Compliance claims require formal validation, controls, and evidence outside the current project scope.

Implications:

- Product copy, documentation, and UI must avoid unsupported compliance claims.
- The application may support auditability and quality workflows without claiming formal compliance.

## 2026-07-30: Local MySQL and OpenAI Scaffold

Decision:

Use React, TypeScript, Redux Toolkit, Vite, and Google Inter on the frontend. Use Python, FastAPI, SQLAlchemy 2, Alembic, PyMySQL, and MySQL 8 or newer on the backend. Do not use Docker for the local scaffold.

Rationale:

The current assignment requires normal Windows terminal commands, a local MySQL service, and no container infrastructure.

Implications:

- No Dockerfiles, Compose files, Kubernetes files, PostgreSQL configuration, or SQLite main database configuration should exist.
- MySQL must be configured through backend environment variables.
- The application must start even when MySQL is unavailable and report degraded health.

## 2026-07-30: OpenAI Provider Is Server-Side Only

Decision:

Use OpenAI API as the configured LLM provider for later phases. `OPENAI_API_KEY` must remain server-side and must not be exposed to React.

Rationale:

The frontend must never receive API provider secrets, and AI functionality is outside the current scaffolding task.

Implications:

- No frontend variable should start with `VITE_OPENAI`.
- No endpoint should return `OPENAI_API_KEY`.
- No OpenAI or LangGraph calls should be implemented in the scaffold phase.
- `OPENAI_MODEL` must be configured through environment variables rather than hardcoded throughout the codebase.

## 2026-07-30: Initial MySQL Database Layer

Decision:

Create the first durable schema with MySQL-compatible SQLAlchemy models, one Alembic initial revision, append-only repositories for audit/version history, idempotent fictional seed data, and read-only reference endpoints.

Rationale:

The complaint workflow requires traceability, deterministic snapshots, evidence preservation, and connected pharmaceutical context before AI behavior is introduced.

Implications:

- UUIDs are stored as `CHAR(36)` and generated in Python.
- JSON uses MySQL `JSON`; PostgreSQL-specific types are not allowed.
- Complaint versions and audit events are append-only at the repository layer.
- Seeded pharmaceutical records must stay clearly fictional demonstration data.
- Migration and database tests must use a safe MySQL test database whose name ends in `_test`.
