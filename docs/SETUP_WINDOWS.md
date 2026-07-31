# Windows Setup

Use these commands from Windows PowerShell.

## Install Prerequisites

- Install Python 3.12 or newer.
- Install Node.js 20 or newer and include npm in PATH.
- Install MySQL Server 8 or newer.

If npm is blocked by PowerShell script policy:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
npm --version
```

## MySQL Databases

Open MySQL Command Line Client as root and run:

```sql
CREATE DATABASE pharmaq_sentinel CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE pharmaq_sentinel_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'pharmaq_user'@'localhost' IDENTIFIED BY 'replace_with_local_password';
CREATE USER 'pharmaq_test_user'@'localhost' IDENTIFIED BY 'replace_with_test_password';
GRANT ALL PRIVILEGES ON pharmaq_sentinel.* TO 'pharmaq_user'@'localhost';
GRANT ALL PRIVILEGES ON pharmaq_sentinel_test.* TO 'pharmaq_test_user'@'localhost';
FLUSH PRIVILEGES;
```

If the user already exists, run:

```sql
ALTER USER 'pharmaq_user'@'localhost' IDENTIFIED BY 'replace_with_local_password';
ALTER USER 'pharmaq_test_user'@'localhost' IDENTIFIED BY 'replace_with_test_password';
```

## Environment

```powershell
cd C:\Users\diyav\OneDrive\Documents\assignment
Copy-Item .env.example .env
notepad .env
```

Set `DATABASE_URL` and `TEST_DATABASE_URL` with local passwords. Do not commit `.env`.

## Backend

```powershell
cd C:\Users\diyav\OneDrive\Documents\assignment\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
python -m app.utilities.seed_database
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend

```powershell
cd C:\Users\diyav\OneDrive\Documents\assignment\frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Demo Documents

```powershell
cd C:\Users\diyav\OneDrive\Documents\assignment\backend
.\.venv\Scripts\Activate.ps1
python -m app.utilities.generate_demo_documents
```
