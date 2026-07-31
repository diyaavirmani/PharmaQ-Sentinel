# Troubleshooting

## `npm` Is Blocked In PowerShell

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
npm --version
```

## `pnpm` Is Not Recognized

Use npm commands from the README, or install pnpm through Corepack from an administrator shell:

```powershell
corepack enable
corepack prepare pnpm@latest --activate
```

If Corepack cannot write to `C:\Program Files\nodejs`, run PowerShell as administrator or use npm.

## MySQL Access Denied

Check that `.env` uses the same host used when creating the MySQL user. If the user was created for `localhost`, use `localhost` in `DATABASE_URL`. If it was created for `127.0.0.1`, use `127.0.0.1`.

## Database Exists Or User Exists

Use `ALTER USER` instead of `CREATE USER`:

```sql
ALTER USER 'pharmaq_user'@'localhost' IDENTIFIED BY 'replace_with_local_password';
```

## Backend Health Is Degraded

The API process is running, but MySQL is unavailable. Confirm:

- MySQL Windows service is started.
- Port `3306` is correct.
- Database name exists.
- Password in `.env` matches MySQL.
- URL includes `charset=utf8mb4`.

## Alembic Cannot Connect

From `backend`:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\check_database.py
alembic current
```

## Test Database Refuses To Run

The test database name must end with `_test`. This protects the development database from destructive test setup.

## CORS Errors

Set:

```text
BACKEND_CORS_ORIGINS=http://localhost:5173
```

Restart the backend after editing `.env`.

## OpenAI Is Unavailable

The app can start without OpenAI. Check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ai/status
```

Live calls require `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env`.
