# Testing

## Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
ruff check .
pytest
```

The backend test suite requires a safe MySQL test database from `TEST_DATABASE_URL`. The database name must end in `_test`; tests refuse unsafe destructive setup.

Covered areas include:

- Alembic migration on empty MySQL test database.
- MySQL-specific UUID, JSON, decimal, timestamp, relationship, and restriction behavior.
- Seed idempotency.
- Complaint draft lifecycle.
- Document parser security.
- OpenAI gateway with mocked provider calls.
- LangGraph route behavior.
- Batch Impact, Quality War Room, Investigation Support, QMS Ledger, and inspection brief generation.

## Frontend

```powershell
cd frontend
npm test -- --run
npm run typecheck
npm run build
npm run test:ui
```

The UI contract tests verify:

- Two-panel workspace structure.
- Left form before assistant.
- Approximate 59/41 desktop column ratio.
- Read-only complaint fields.
- Assistant upload and extraction progress placement.
- Advanced modules below the workspace.
- Overlay drawers instead of layout shifts.
- Mobile stacked layout.

## Manual Smoke Checks

1. Start MySQL.
2. Run `alembic upgrade head`.
3. Run `python -m app.utilities.seed_database` twice.
4. Start backend and frontend.
5. Open `/health`, `/api/v1/ai/status`, and the workspace.
6. Generate demo documents and upload a fictional complaint.
7. Save a complaint and preview the inspection brief.

Do not claim success for live OpenAI behavior unless a live call was intentionally configured and tested.
