# PharmaQ Sentinel

**AI-native pharmaceutical complaint intelligence system for API and Finished Dosage Form manufacturers**

PharmaQ Sentinel converts unstructured customer complaints from natural-language messages, PDFs, DOCX files, TXT files, and emails into structured, traceable, human-reviewed quality records.

> AI-generated extraction, classifications, investigation hypotheses, and recommendations require review and approval by authorised quality personnel. This project is a demonstration system and does not itself establish regulatory compliance.

---

## Product Overview

Pharmaceutical complaints often arrive through emails, distributor letters, call summaries, or informal text. Quality teams must identify the product, batch, affected quantity, complaint category, patient-safety signals, and supporting evidence before starting an investigation.

PharmaQ Sentinel provides one controlled workspace where an AI assistant can:

1. Extract complaint details from natural language.
2. Populate a read-only complaint form.
3. Apply natural-language corrections without removing unrelated fields.
4. Extract complaint information from uploaded documents.
5. Identify missing information.
6. Suggest initial severity, priority, and routing.
7. Preserve field-level evidence and change history.
8. Connect a complaint to batch and manufacturing records.
9. Run a multidisciplinary AI Quality War Room.
10. Save the reviewed complaint to a QMS Ledger.
11. Generate an inspection-ready complaint brief.

The AI prepares a structured draft and decision-support package. Authorised quality personnel remain responsible for review, investigation, approval, and final decisions.

---

## Core Workflow

```mermaid
flowchart TD
    A[Natural-language complaint or document] --> B[AI Complaint Intake Assistant]
    B --> C[Structured extraction]
    C --> D[Validation and patch merge]
    D --> E[Read-only complaint form]
    E --> F[Completeness checker]
    F --> G[Risk and safety routing]
    G --> H[Evidence Lock and audit trail]
    H --> I[Batch Blast-Radius analysis]
    I --> J[AI Quality War Room]
    J --> K[Investigation and CAPA considerations]
    K --> L[Human QA review]
    L --> M[Save Complaint]
    M --> N[QMS Ledger]
    N --> O[Inspection-ready complaint brief]
```

---

## Mandatory Features

### Log Complaint Tool

The user enters a complaint through the AI assistant.

Example:

```text
Apollo Pharmacy reported 12 discoloured Amoxicillin Capsules 500 mg
from batch AMX240602. Manufacturing month March 2026 and expiry month
February 2028.
```

The system extracts supported fields, populates the read-only form, records evidence, identifies missing information, and prepares an initial risk assessment.

### Edit Complaint Tool

The user corrects complaint data through natural language.

```text
Sorry, the batch is BMX240602 and the affected quantity is 48 capsules.
```

Only the explicitly requested fields are changed. Every unrelated field remains unchanged.

### Document Extraction Tool

Supported sources:

- PDF
- DOCX
- TXT
- EML

The original file is preserved, its checksum is recorded, and page- or paragraph-level evidence is linked to populated fields.

### AI Risk Classification

The system suggests:

- Critical
- Major
- Minor
- Undetermined

It also produces suggested priority, patient-harm level, quality-defect signal, possible adverse-event signal, possible counterfeit signal, recommended route, supporting evidence, contradictory evidence, confidence, limitations, and follow-up questions.

All classifications require QA confirmation.

---

## Standout Features

### 1. Batch Blast-Radius Digital Twin

An interactive graph connects the complaint to:

- Product and batch
- Raw-material or API lots
- Packaging-material lots
- Suppliers
- Manufacturing and packaging lines
- Equipment
- Deviations
- CAPAs
- Historical complaints
- Related batches
- Distribution locations
- Warehouse inventory

It answers:

> What else may require assessment because of this complaint?

The Containment Simulator estimates the potentially affected scope without changing real records.

```text
SIMULATION ONLY — No batch, inventory, shipment, or recall status is changed.
```

### 2. AI Quality War Room

A bounded LangGraph subgraph coordinates:

- QA Risk Agent
- Manufacturing Investigator
- Packaging and Supplier Agent
- Pharmacovigilance Agent
- Compliance Auditor Agent
- Consensus Agent

The Compliance Auditor challenges unsupported conclusions.

```text
Rejected claim:
Packaging seal failure is the confirmed root cause.

Reason:
No approved seal-integrity result or completed investigation currently
confirms the hypothesis.
```

Only concise findings, evidence, hypotheses, disagreements, and limitations are displayed. Hidden chain-of-thought is never returned.

### Evidence Lock and Inspector Replay

Every populated or corrected field can be traced to:

- Original message or document
- Page or paragraph
- Source excerpt
- Confidence
- Extraction method
- Previous values
- User corrections
- Timestamp
- Model and prompt metadata

Inspector Replay shows the complete chronological quality record.

### Pharmaceutical Safety Router

The system distinguishes:

- Product quality complaint
- Possible adverse event
- Quality complaint plus adverse event
- Counterfeit or tampering concern
- Distribution or storage issue
- Service-only complaint
- Undetermined case

It may recommend review by Quality Assurance, Pharmacovigilance, Regulatory Affairs, Supply Chain, Anti-counterfeit, or Customer Service. It does not determine legal reportability.

### Investigation Playbooks

Complaint-specific playbooks are available for:

- Capsule or tablet discolouration
- Broken tablets
- Blister leakage
- Wrong label
- Wrong product or strength
- Foreign matter
- API assay, impurity, or moisture discrepancy
- Suspected counterfeit
- Sterility concern
- Storage or transportation excursion
- Quality complaint plus possible adverse event

The system separates immediate correction, containment, corrective action, preventive action, and effectiveness-check considerations.

---

## Reference UI Contract

The reference interface remains the main application workspace.

```text
┌───────────────────────────────────────────────────────────────┐
│ Log Customer Complaint       │ AI Complaint Intake Assistant │
│                               │                               │
│ Read-only complaint form      │ Upload complaint document     │
│ Product and batch details     │ Extraction progress           │
│ Complaint details             │ Assistant conversation        │
│ Initial assessment            │ Chat composer                 │
│                               │                               │
│ Reset Form    Save Complaint  │ AI disclaimer                 │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ Quality Intelligence                                           │
│ Batch Intelligence | Quality War Room | Evidence & Audit      │
│ Investigation Support                                          │
└───────────────────────────────────────────────────────────────┘
```

Rules:

- Complaint form remains on the left.
- AI assistant remains on the right.
- Desktop proportion remains approximately 59% / 41%.
- Complaint fields are always read-only.
- Log, Edit, and Document Extraction use the same assistant.
- No permanent third column is introduced.
- Advanced features appear below the workspace.
- Evidence opens in overlay drawers or modals.
- Google Inter is used throughout.
- Mobile layout stacks the form before the assistant.

---

## Technology Stack

### Frontend

- React
- TypeScript
- Redux Toolkit
- RTK Query
- React Router
- Google Inter
- `@xyflow/react`
- Vitest
- React Testing Library
- Playwright

### Backend

- Python
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PyMySQL
- MySQL 8+

### AI

- LangGraph
- OpenAI API
- OpenAI Responses API
- Pydantic Structured Outputs
- Model selected through environment variables

### Document Processing

- PyMuPDF
- python-docx
- Python email parser
- Secure plain-text decoding

### Explicitly Not Used

- Docker
- PostgreSQL
- Frontend LLM calls
- Editable complaint fields
- Automatic recalls, batch holds, CAPA approvals, or regulatory submissions

---

## Architecture

```mermaid
flowchart LR
    UI[React UI] --> RX[Redux Toolkit and RTK Query]
    RX --> API[FastAPI API]
    API --> LG[LangGraph]
    LG --> OAI[OpenAI Gateway]
    LG --> QS[Quality Services]
    QS --> DB[(MySQL)]
    API --> DOC[Document Parsers]
    DOC --> DB
    DB --> BI[Batch Impact Engine]
    DB --> WR[Quality War Room]
    API --> REP[Inspection Brief Generator]
```

The application separates:

1. Redux UI state.
2. LangGraph execution state.
3. Mutable `ComplaintDraft` state in MySQL.
4. Saved `Complaint` and immutable `ComplaintVersion` snapshots.

MySQL is the official application source of truth.

---

## Repository Structure

```text
PharmaQ-Sentinel/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── styles/
│   │   └── types/
│   ├── tests/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utilities/
│   │   └── main.py
│   ├── alembic/
│   ├── storage/uploads/
│   ├── tests/
│   ├── pyproject.toml
│   └── alembic.ini
├── docs/
├── scripts/
├── .env.example
├── .gitignore
├── AGENTS.md
└── README.md
```

---

## Prerequisites

Install:

- Python 3.11+
- Node.js 20+
- npm
- MySQL Community Server 8+
- Git

Recommended on Windows:

- PowerShell
- MySQL Workbench
- Visual Studio Code

---

## Environment Configuration

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Example:

```env
APP_NAME=PharmaQ Sentinel
APP_ENV=development
APP_VERSION=0.1.0
DEBUG=true

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
BACKEND_CORS_ORIGINS=http://localhost:5173

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=pharmaq_sentinel
MYSQL_USER=pharmaq_user
MYSQL_PASSWORD=CHANGE_THIS_LOCAL_PASSWORD

DATABASE_URL=mysql+pymysql://pharmaq_user:CHANGE_THIS_LOCAL_PASSWORD@127.0.0.1:3306/pharmaq_sentinel?charset=utf8mb4
TEST_DATABASE_URL=mysql+pymysql://pharmaq_test_user:CHANGE_THIS_TEST_PASSWORD@127.0.0.1:3306/pharmaq_sentinel_test?charset=utf8mb4

LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_CONTEXT_MODEL=
OPENAI_TIMEOUT_SECONDS=60
OPENAI_MAX_RETRIES=2
OPENAI_TEMPERATURE=0
OPENAI_MAX_OUTPUT_TOKENS=3000
OPENAI_ENABLE_LIVE_TESTS=false
OPENAI_LOG_PROMPTS=false

DEMO_AI_MODE=live

VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1

UPLOAD_DIRECTORY=backend/storage/uploads
MAX_UPLOAD_SIZE_MB=10
```

Never commit `.env`. Never expose `OPENAI_API_KEY` through a `VITE_` variable.

---

## MySQL Setup

Run in MySQL Workbench or the MySQL command-line client:

```sql
CREATE DATABASE pharmaq_sentinel
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE pharmaq_sentinel_test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'pharmaq_user'@'localhost'
IDENTIFIED BY 'CHANGE_THIS_LOCAL_PASSWORD';

CREATE USER 'pharmaq_test_user'@'localhost'
IDENTIFIED BY 'CHANGE_THIS_TEST_PASSWORD';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON pharmaq_sentinel.*
TO 'pharmaq_user'@'localhost';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES, DROP
ON pharmaq_sentinel_test.*
TO 'pharmaq_test_user'@'localhost';

FLUSH PRIVILEGES;
```

Check the Windows service:

```powershell
Get-Service *mysql*
Start-Service MySQL80
```

The service name may differ.

---

## Backend Setup

```powershell
cd backend

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -e ".[dev]"

alembic upgrade head
python -m app.utilities.seed_database
python -m app.utilities.generate_demo_documents

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful URLs:

```text
API:        http://127.0.0.1:8000
Swagger:    http://127.0.0.1:8000/docs
Health:     http://127.0.0.1:8000/api/v1/health
AI status:  http://127.0.0.1:8000/api/v1/ai/status
```

---

## Frontend Setup

Open another PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

Build and type-check:

```powershell
npm run typecheck
npm run build
```

---

## Database Migrations

```powershell
cd backend

alembic current
alembic upgrade head
alembic revision --autogenerate -m "describe schema change"
alembic downgrade -1
```

Never run destructive migration tests against the development database. The test database name must end in `_test`.

---

## Seed Data

```powershell
cd backend
python -m app.utilities.seed_database
```

The fictional seed scenario includes:

- Amoxicillin Capsules 500 mg
- Amoxicillin API
- Paracetamol Tablets 500 mg
- Ceftriaxone Injection
- Omeprazole Capsules 20 mg
- Batches `BMX240602`, `BMX240603`, `BMX240604`
- Packaging line `PL-04`
- Deviation `DEV-2026-023`
- Linked CAPA
- Shared packaging-material lot
- Historical discolouration complaints
- Distribution to Delhi, Mumbai, and Jaipur
- Warehouse inventory
- Additional API and FDF complaints

The command is idempotent and should not duplicate records when run twice.

---

## Demo Documents

```powershell
cd backend
python -m app.utilities.generate_demo_documents
```

Expected fictional files:

- Amoxicillin capsule discolouration PDF
- API assay complaint DOCX
- Packaging leakage TXT
- Customer complaint EML

Each should be marked:

```text
DEMONSTRATION DATA — NOT A REAL PHARMACEUTICAL RECORD
```

---

## API Overview

### Health and AI

```text
GET /health
GET /api/v1/health
GET /api/v1/ai/status
```

### Complaint Drafts

```text
POST /api/v1/complaint-drafts
GET  /api/v1/complaint-drafts/{draft_id}
POST /api/v1/complaint-drafts/{draft_id}/reset
GET  /api/v1/complaint-drafts/{draft_id}/status
```

### Assistant

```text
POST /api/v1/complaint-drafts/{draft_id}/messages
GET  /api/v1/complaint-drafts/{draft_id}/messages
```

### Attachments

```text
POST /api/v1/complaint-drafts/{draft_id}/attachments
GET  /api/v1/complaint-drafts/{draft_id}/attachments/{attachment_id}/status
```

### Evidence and Timeline

```text
GET /api/v1/complaint-drafts/{draft_id}/evidence
GET /api/v1/complaint-drafts/{draft_id}/evidence/{field_name}
GET /api/v1/complaint-drafts/{draft_id}/timeline
```

### Batch Intelligence

```text
POST /api/v1/complaint-drafts/{draft_id}/batch-impact
POST /api/v1/complaint-drafts/{draft_id}/batch-impact/simulate
```

### Quality War Room

```text
POST /api/v1/complaint-drafts/{draft_id}/quality-war-room/runs
GET  /api/v1/complaint-drafts/{draft_id}/quality-war-room/runs
GET  /api/v1/complaint-drafts/{draft_id}/quality-war-room/runs/{run_id}
GET  /api/v1/complaint-drafts/{draft_id}/quality-war-room/runs/{run_id}/stream
```

### Investigation Support

```text
POST /api/v1/complaint-drafts/{draft_id}/duplicate-analysis
POST /api/v1/complaint-drafts/{draft_id}/investigation-playbook
```

### QMS Ledger

```text
POST /api/v1/complaint-drafts/{draft_id}/save
GET  /api/v1/complaints
GET  /api/v1/complaints/{complaint_id}
GET  /api/v1/complaints/{complaint_id}/versions
GET  /api/v1/complaints/{complaint_id}/timeline
```

### Inspection Brief

```text
GET /api/v1/complaints/{complaint_id}/inspection-brief?format=json
GET /api/v1/complaints/{complaint_id}/inspection-brief?format=html
GET /api/v1/complaints/{complaint_id}/inspection-brief?format=pdf
```

---

## Testing

### Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

pytest
pytest --cov=app --cov-report=term-missing
```

Optional live AI tests:

```powershell
$env:OPENAI_ENABLE_LIVE_TESTS="true"
pytest -m live_ai
```

### Frontend

```powershell
cd frontend

npm test -- --run
npm run typecheck
npm run build
```

### End-to-End

```powershell
npx playwright install
npx playwright test
```

Important coverage areas:

- Draft creation and restoration
- Read-only form enforcement
- Log Complaint extraction
- Edit preservation
- Partial-date handling
- Document MIME and size validation
- Evidence and audit events
- Severity floors and safety routing
- Batch graph connections
- Containment simulation non-mutation
- War Room bounded iterations
- Hidden reasoning not exposed
- Save idempotency
- Version checksum
- PDF generation
- UI screenshot regression
- Mobile stacked layout

---

## Suggested Demo Sequence

1. Open the empty read-only Complaint Workspace.
2. Upload the fictional Amoxicillin complaint PDF.
3. Show extracted complaint fields and initial Major severity.
4. Correct batch and quantity through chat.
5. Open Evidence Lock and show original versus corrected values.
6. Run Batch Blast-Radius and containment simulation.
7. Run the AI Quality War Room.
8. Add a possible adverse-event statement.
9. Show Pharmacovigilance routing and follow-up questions.
10. Open duplicate analysis and investigation playbook.
11. Save the complaint.
12. Open QMS Ledger and Inspector Replay.
13. Preview and download the inspection-ready brief.

---

## Security and Data Integrity

- OpenAI calls are server-side only.
- API keys and database credentials are never returned to React.
- Raw model outputs are validated with Pydantic.
- No `eval` or model-generated code execution is used.
- Missing values remain null.
- User corrections preserve original evidence.
- Deterministic rules create minimum severity floors.
- Hidden chain-of-thought is not stored or returned.
- Uploaded files are size-limited, MIME-checked, checksum-protected, and stored outside public static paths.
- Audit and complaint-version records are append-only through normal repositories.
- Saved complaints cannot be silently modified.
- Containment simulation does not mutate inventory or batch status.

---

## Known Limitations

- This is a focused complaint-management prototype, not a full enterprise eQMS.
- It does not implement complete document control, training, LIMS, MES, supplier qualification, recall execution, or regulatory submission.
- AI outputs may be incorrect.
- Production computer-system validation and formal model governance are outside scope.
- OCR for image-only files may be limited or disabled.
- Seeded pharmaceutical records are fictional.
- Batch relationships do not prove causation.
- Pharmacovigilance routing does not determine reportability.
- Save Complaint is not a legally valid electronic signature.
- Application-level append-only controls are not equivalent to tamper-proof infrastructure.
- Local performance measurements must not be represented as production benchmarks.

---

## Regulatory Disclaimer

PharmaQ Sentinel is a demonstration and portfolio project. It must not be represented as:

- FDA-approved software
- A validated GxP system
- Automatically compliant with 21 CFR Part 11
- Automatically compliant with EU GMP
- Automatically compliant with ICH Q7, Q9, or Q10
- A replacement for authorised QA, Pharmacovigilance, Regulatory Affairs, or medical review
- An automated recall or regulatory-reporting system

A production implementation would require formal validation, access controls, SOPs, training, security testing, infrastructure qualification, change control, model governance, and organisation-specific regulatory review.

---

## Project Positioning

> PharmaQ Sentinel is not only an AI form-filling chatbot. It is a pharmaceutical quality-intelligence layer that converts unstructured complaints into structured records, assesses possible patient and batch impact, conducts a bounded multidisciplinary AI review, preserves evidence for every value, and gives QA an auditable decision-support package.

---

## License

Add the appropriate licence before public distribution. Keep the repository private when required by the assignment or evaluator.
