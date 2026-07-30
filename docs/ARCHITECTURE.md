# PharmaQ Sentinel Architecture

## Mandatory Stack

Frontend:

- React
- TypeScript
- Redux Toolkit
- React Redux
- Google Inter font
- Custom CSS or CSS Modules
- No large UI component library

Backend:

- Python
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- MySQL 8 or newer

AI:

- LangGraph
- OpenAI API
- OpenAI API keys remain server-side only.
- Model selection must be configuration-driven through backend environment variables.

Do not introduce Docker, PostgreSQL, Groq, Tailwind unless already present, a second design system, a large UI component library, a separate chatbot page, or a separate document upload page.

## Main Layers

### Frontend

The frontend is a React and TypeScript application using Redux Toolkit for client state and typed service clients for API access. It renders complaint drafts, evidence, missing information, audit timelines, batch impact analysis, and war-room views in later phases.

Complaint form fields must be read-only when complaint workflows are implemented. Corrections must be submitted through the AI Complaint Intake Assistant as natural-language instructions. The frontend must never receive or store OpenAI API keys, database URLs, or MySQL credentials.

The primary complaint experience is the locked Complaint Workspace defined in `docs/UI_CONTRACT.md`. It must remain a two-panel interface with the read-only Log Customer Complaint form on the left and the AI Complaint Assistant on the right. Log Complaint, Edit Complaint, and Document Extraction workflows must operate inside this same workspace and update the same Redux complaint draft.

Advanced complaint intelligence features must appear below the locked workspace in the collapsible Quality Intelligence Dock. Batch Intelligence, Quality War Room, Evidence & Audit, and Investigation Support use tabs inside that dock rather than separate pages or extra permanent columns.

### Backend API

The backend API is a FastAPI application. It exposes authenticated endpoints for complaint intake, document upload, draft retrieval, natural-language correction, risk recommendation retrieval, audit history, QMS ledger commitment, batch impact analysis, and war-room state.

The API validates request and response payloads with Pydantic v2 models. It must treat AI output as untrusted draft data until validated and persisted through application services.

### Application Services

Application services coordinate business workflows. They enforce data integrity rules, perform patch-and-merge operations, create immutable versions, write audit events, and call AI orchestration or repositories as needed.

Application services are the correct place for complaint lifecycle rules. Route handlers should remain thin.

### LangGraph Orchestration

LangGraph manages AI workflows such as complaint extraction, correction interpretation, missing information detection, risk recommendation, batch impact reasoning, and quality-war-room subgraph interactions.

LangGraph conversation state must not be treated as the durable complaint record. It is orchestration state for multi-step AI workflows.

### OpenAI Model Gateway

The OpenAI model gateway will be the backend-only integration layer for OpenAI in later phases. It owns provider configuration, model selection, request execution, response metadata, and error normalization.

The gateway must:

- Keep API keys server-side only.
- Use a model configured through environment variables.
- Persist or return the actual model used for every AI operation.
- Return enough metadata for audit events.

### Repositories

Repositories encapsulate database access using SQLAlchemy 2. They should not contain AI prompts, UI decisions, or business workflow branching beyond persistence-specific concerns.

Repository methods should make transaction boundaries explicit through application services or unit-of-work patterns.

### MySQL

MySQL 8 or newer is the system of record for complaint drafts, committed complaint records, immutable versions, audit events, uploaded document metadata, extracted evidence, model-run metadata, batch-impact results, and war-room state when those phases are implemented.

Schema changes must be managed through Alembic migrations.

### Document Extraction

The document extraction layer ingests PDF, DOCX, EML, images, and plain text sources. It preserves original uploads unchanged and stores derived artifacts separately.

Responsibilities include:

- File metadata capture.
- Text extraction.
- OCR for images when implemented.
- Email header and body extraction for EML.
- Source span or region mapping where possible.
- Tool and timestamp metadata.

Document extraction can feed LangGraph, but it must not overwrite complaint fields directly. Extracted data must pass through application services and audit-aware persistence.

### Audit System

The audit system records every mutation. Each mutation event must contain:

- Entity type and identifier.
- Field or path changed.
- Old value.
- New value.
- Timestamp.
- Actor.
- Tool or subsystem.
- Reason.
- Actual model used when AI participated.
- Source evidence or instruction reference when applicable.

Audit events are append-only. They must not be edited as part of normal application behavior.

### Batch-Impact Engine

The batch-impact engine powers the Batch Blast-Radius Digital Twin. It evaluates possible related batches, lots, products, sites, suppliers, components, distribution exposure, and similar defect patterns.

The engine may use deterministic rules, database queries, and AI-assisted reasoning. AI-assisted conclusions must be labeled as recommendations with evidence, confidence, limitations, and actual model used.

### Quality-War-Room Subgraph

The quality-war-room subgraph coordinates AI-assisted review for open complaints. It can summarize complaint status, identify missing information, surface evidence, propose discussion prompts, and reason about possible investigation paths.

It must maintain a strict distinction between AI suggestions and authorized human decisions.

## State Model

### LangGraph Conversation State

LangGraph conversation state is transient or workflow-scoped state used to coordinate AI steps, tool calls, intermediate reasoning outputs, extracted candidates, and assistant conversation context.

It is not the authoritative complaint record. It may be persisted for traceability, but complaint truth must live in database entities controlled by application services.

### Complaint Draft Database State

Complaint draft database state is the current working version of a complaint before QMS ledger commitment. It is durable and queryable.

Draft fields may be created or corrected only through extraction workflows or natural-language assistant corrections. Each accepted change must create audit events and immutable versions.

### Committed Complaint Record

A committed complaint record is the reviewed complaint state accepted into the QMS ledger. It should be treated as a formal downstream quality record within the application, while avoiding claims of regulatory validation or Part 11 compliance.

Committed records should be linked back to source documents, evidence, draft history, immutable versions, and audit events.

### Immutable Complaint Versions

Immutable complaint versions are snapshots or versioned representations of complaint state after meaningful mutations. They support review, rollback analysis, audit reconstruction, and QMS ledger traceability.

Versions must not be modified after creation. Corrections create new versions.

### Audit Events

Audit events are append-only records of mutations and system actions. They explain how and why data changed, who or what changed it, what old and new values were involved, and which model was actually used when AI participated.

Audit events are not replacements for immutable complaint versions. Versions preserve state; audit events preserve change history and rationale.

## Data Flow Overview

1. User submits text or uploads a source document.
2. Backend preserves the original source unchanged.
3. Document extraction creates derived text and source mappings.
4. LangGraph extraction proposes structured complaint fields.
5. Application services validate, patch, merge, version, and audit the draft.
6. Frontend displays the read-only complaint draft with evidence and missing information.
7. User submits natural-language corrections through the assistant.
8. LangGraph proposes a correction patch.
9. Application services merge only approved patch fields, preserve unrelated values, create versions, and audit changes.
10. AI risk assessment, batch-impact analysis, and war-room outputs are generated as recommendations with evidence, confidence, limitations, and actual model used.
11. Authorized users review and commit the complaint draft into the QMS ledger.

## Security Boundaries

- AI provider calls occur only on the backend.
- OpenAI API keys are stored only in server-side secret configuration.
- Uploaded documents are preserved unchanged and access-controlled.
- Frontend configuration must not include secrets.
- Logs must avoid leaking credentials or sensitive source document contents beyond operational necessity.
