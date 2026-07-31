# PharmaQ Sentinel

PharmaQ Sentinel is a local full-stack foundation for an AI-assisted pharmaceutical complaint intelligence application. The current codebase includes infrastructure, health checks, a MySQL database layer, deterministic fictional seed data, read-only reference endpoints, the locked Complaint Workspace, assistant-mediated text complaint logging/editing, and document extraction for PDF, DOCX, TXT, and EML uploads. Batch Blast-Radius and Quality War Room modules are intentionally not implemented yet.

## Mandatory Stack

- Frontend: React, TypeScript, Redux Toolkit, Google Inter font, Vite
- Backend: Python, FastAPI, SQLAlchemy 2, PyMySQL
- Database: MySQL 8 or newer
- Later AI framework: LangGraph
- Later LLM provider: server-side only

Docker is intentionally not used in this project.

## Directory Structure

```text
/
  frontend/
  backend/
  docs/
  scripts/
  .env.example
  .gitignore
  README.md
  AGENTS.md
```

## Prerequisites

- Windows PowerShell
- Python 3.12 or newer
- Node.js 20 or newer
- MySQL 8 or newer

MySQL setup is documented in [docs/MYSQL_SETUP.md](C:/Users/diyav/OneDrive/Documents/assignment/docs/MYSQL_SETUP.md).

## Environment Setup

From the repository root:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with local MySQL credentials. Do not commit `.env`.

The frontend may only read variables prefixed with `VITE_`. Do not create frontend variables for AI provider keys, database URLs, or MySQL credentials.

OpenAI setup is backend-only and documented in [docs/OPENAI_INTEGRATION.md](C:/Users/diyav/OneDrive/Documents/assignment/docs/OPENAI_INTEGRATION.md). The API starts without an OpenAI key; `/api/v1/ai/status` reports unavailable until `OPENAI_API_KEY` and `OPENAI_MODEL` are configured.

## Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/v1/health`

Health endpoints return HTTP 200 for both `healthy` and `degraded` states. A degraded response means the API process is running but MySQL is unavailable.

Check MySQL connectivity:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts\check_database.py
```

Run migrations:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

Seed fictional development records:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.utilities.seed_database
```

Verify migration round trips against `TEST_DATABASE_URL`:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts\verify_migrations.py
```

Reference endpoints:

- `http://127.0.0.1:8000/api/v1/reference/products`
- `http://127.0.0.1:8000/api/v1/reference/batches/BMX240602`
- `http://127.0.0.1:8000/api/v1/reference/seed-status`
- `http://127.0.0.1:8000/api/v1/reference/historical-complaints`

AI status endpoint:

- `http://127.0.0.1:8000/api/v1/ai/status`

Complaint document extraction endpoints:

- `POST http://127.0.0.1:8000/api/v1/complaint-drafts/{draft_id}/attachments`
- `GET http://127.0.0.1:8000/api/v1/complaint-drafts/{draft_id}/attachments/{attachment_id}/status`

Generate fictional demo upload documents:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.utilities.generate_demo_documents
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

- `http://localhost:5173`

## Tests

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

Frontend:

```powershell
cd frontend
npm test -- --run
npm run typecheck
npm run build
```

## Common Errors

- Access denied for MySQL user: confirm the username, password, host, and grants in `.env`.
- Connection refused: confirm the MySQL Windows service is running and listening on port `3306`.
- CORS blocked in browser: confirm `BACKEND_CORS_ORIGINS` includes `http://localhost:5173`.
- Backend degraded: the API is running, but the configured MySQL connection check failed.

## Security Warning

Never commit API keys, MySQL passwords, `.env`, or production data. AI provider keys are backend-only and must never be exposed to React or any `VITE_` variable.
