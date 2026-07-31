# API Reference

Base URL: `http://127.0.0.1:8000/api/v1`

## Health

- `GET /health`
- `GET /api/v1/health`

Returns service status, version, and MySQL connectivity.

## AI Status

- `GET /api/v1/ai/status`

Returns safe OpenAI configuration status and `demo_ai_mode`. It never returns API keys.

- `POST /api/v1/ai/test-connection`

Development only when `APP_ENV=development` and `OPENAI_ENABLE_TEST_CONNECTION=true`.

## Complaint Drafts

- `POST /complaint-drafts`
- `GET /complaint-drafts/{draft_id}`
- `GET /complaint-drafts/{draft_id}/status`
- `POST /complaint-drafts/{draft_id}/reset`
- `PATCH /complaint-drafts/{draft_id}/development-patch`

The development patch endpoint is local testing only and must be disabled outside development.

## Assistant And Uploads

- `GET /complaint-drafts/{draft_id}/messages`
- `POST /complaint-drafts/{draft_id}/messages`
- `POST /complaint-drafts/{draft_id}/attachments`
- `GET /complaint-drafts/{draft_id}/attachments/{attachment_id}/status`

Uploads preserve original files outside public frontend paths. API responses exclude internal storage paths.

## Evidence And Timeline

- `GET /complaint-drafts/{draft_id}/evidence`
- `GET /complaint-drafts/{draft_id}/evidence/{field_name}`
- `GET /complaint-drafts/{draft_id}/timeline`

Evidence and audit endpoints are read-focused and support review of field history.

## QMS Ledger

- `POST /complaint-drafts/{draft_id}/save`
- `GET /complaints`
- `GET /complaints/{complaint_id}`
- `GET /complaints/{complaint_id}/versions`
- `GET /complaints/{complaint_id}/timeline`

Saved complaints create immutable complaint versions.

## Inspection Brief

- `GET /complaints/{complaint_id}/inspection-brief?format=json`
- `GET /complaints/{complaint_id}/inspection-brief?format=html`
- `GET /complaints/{complaint_id}/inspection-brief?format=pdf`

The brief is generated from the saved complaint version snapshot plus linked append-only records. Unsupported formats return `422`.

## Reference Data

- `GET /reference/products`
- `GET /reference/batches/{batch_number}`
- `GET /reference/seed-status`
- `GET /reference/historical-complaints`

Reference data is fictional demonstration data when seeded locally.

## Intelligence

- `POST /complaint-drafts/{draft_id}/batch-impact`
- `POST /complaint-drafts/{draft_id}/batch-impact/simulate`
- `POST /complaint-drafts/{draft_id}/quality-war-room/runs`
- `GET /complaint-drafts/{draft_id}/quality-war-room/runs`
- `GET /complaint-drafts/{draft_id}/quality-war-room/runs/{run_id}`
- `GET /complaint-drafts/{draft_id}/quality-war-room/runs/{run_id}/stream`
- `POST /complaint-drafts/{draft_id}/duplicate-analysis`
- `POST /complaint-drafts/{draft_id}/investigation-playbook`

Outputs are draft decision support, not authorised quality decisions.
