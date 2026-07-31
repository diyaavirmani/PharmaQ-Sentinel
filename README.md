# PharmaQ Sentinel

**AI-powered pharmaceutical complaint intelligence for API and Finished Dosage Form manufacturers**

PharmaQ Sentinel converts unstructured pharmaceutical complaints from text, PDF, DOCX, TXT, and EML files into structured, traceable, and human-reviewed quality records.

> AI-generated results are recommendations only and require review by authorised quality personnel.

---

## Features

- Natural-language complaint logging
- AI-based complaint editing while preserving unrelated fields
- PDF, DOCX, TXT, and EML complaint extraction
- AI risk classification and priority suggestions
- Complaint completeness checker
- Product Quality and Pharmacovigilance routing
- Field-level evidence, confidence, and correction history
- Duplicate and recurrence detection
- Batch Blast-Radius graph
- Containment simulation
- AI Quality War Room with specialist agents
- Compliance Auditor for unsupported claims
- Investigation and CAPA recommendations
- Inspector Replay and audit timeline
- QMS Ledger for saved complaints
- Inspection-ready PDF complaint brief

---

## Tech Stack

**Frontend:** React, TypeScript, Redux Toolkit, RTK Query, React Router, Google Inter, `@xyflow/react`

**Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic

**AI:** LangGraph, OpenAI Responses API, Pydantic structured outputs

**Database:** MySQL

**Document Processing:** PyMuPDF, python-docx, Python email parser

---

## Workflow

```text
Complaint text or document
        ↓
AI extraction and validation
        ↓
Read-only complaint form
        ↓
Risk and safety routing
        ↓
Evidence and audit trail
        ↓
Batch Intelligence
        ↓
AI Quality War Room
        ↓
Human QA review
        ↓
QMS Ledger and inspection brief
```

---

## Application Routes

```text
/             Landing page
/workspace    Complaint workspace
/qms-ledger   Saved complaints
```

The complaint form remains read-only. Complaint logging, editing, and document extraction happen through the AI assistant.

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- npm
- MySQL 8+
- Git

---

## Environment Setup

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Update the required values in `.env`:

```env
APP_ENV=development
DEBUG=true

BACKEND_CORS_ORIGINS=http://localhost:5173

DATABASE_URL=mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/pharmaq_sentinel?charset=utf8mb4

TEST_DATABASE_URL=mysql+pymysql://TEST_USER:TEST_PASSWORD@127.0.0.1:3306/pharmaq_sentinel_test?charset=utf8mb4

OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_CONTEXT_MODEL=

DEMO_AI_MODE=deterministic

VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1

UPLOAD_DIRECTORY=backend/storage/uploads
MAX_UPLOAD_SIZE_MB=10
```

Use:

```env
DEMO_AI_MODE=deterministic
```

for a stable local demonstration.

Use:

```env
DEMO_AI_MODE=live
```

after configuring a valid OpenAI API key and model.

Never commit the `.env` file.

---

## MySQL Setup

Create the development and test databases:

```sql
CREATE DATABASE pharmaq_sentinel
CHARACTER SET utf8mb4
COLLATE utf8mb4_0900_ai_ci;

CREATE DATABASE pharmaq_sentinel_test
CHARACTER SET utf8mb4
COLLATE utf8mb4_0900_ai_ci;
```

Create MySQL users matching the credentials used in `.env`.

---

## Run the Backend

Open PowerShell:

```powershell
cd backend
```

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run database migrations:

```powershell
alembic upgrade head
```

Seed fictional pharmaceutical data:

```powershell
python -m app.utilities.seed_database
```

Generate demonstration complaint files:

```powershell
python -m app.utilities.generate_demo_documents
```

Start FastAPI:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend URLs:

```text
API:       http://127.0.0.1:8000
Swagger:   http://127.0.0.1:8000/docs
Health:    http://127.0.0.1:8000/api/v1/health
AI Status: http://127.0.0.1:8000/api/v1/ai/status
```

---

## Run the Frontend

Open another PowerShell terminal:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm ci
```

Start the React application:

```powershell
npm run dev
```

Open:

```text
http://localhost:5173
```

---

## Demo Documents

The demo document generator creates fictional files inside:

```text
backend/storage/demo_documents
```

Generated examples include:

- Amoxicillin complaint PDF
- API assay complaint DOCX
- Packaging leakage TXT file
- Customer complaint EML file

All generated records are fictional demonstration data.

---

## Testing

### Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

### Frontend

```powershell
cd frontend
npm test -- --run
npm run typecheck
npm run build
```

### End-to-End

Keep the backend and frontend running, then execute:

```powershell
cd frontend
npx playwright install
npx playwright test
```

---

## Demo Flow

1. Open the landing page.
2. Launch the complaint workspace.
3. Upload the pharmaceutical complaint PDF.
4. Show automatic complaint-form population.
5. Correct the batch and quantity through chat.
6. Open field-level evidence.
7. Show AI risk classification and completeness results.
8. Run Batch Intelligence.
9. Run the containment simulation.
10. Run the AI Quality War Room.
11. Add a possible adverse-event signal.
12. Open duplicate detection and Investigation Support.
13. Save the complaint.
14. Open the QMS Ledger.
15. Show Inspector Replay.
16. Export the inspection-ready complaint brief.

---



---


