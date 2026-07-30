# MySQL Setup

PharmaQ Sentinel uses MySQL 8 or newer for local development. Docker is not used.

## 1. Start The MySQL Service

Open Windows PowerShell and check the service:

```powershell
Get-Service *mysql*
```

Start the service if needed:

```powershell
Start-Service MySQL80
```

The service name may differ depending on your MySQL installation.

## 2. Open MySQL

Use one of these options:

- MySQL Command Line Client
- MySQL Workbench
- PowerShell with the `mysql` command if it is on PATH

Sign in with a local administrator account such as `root`.

## 3. Create Databases

Use the example script at [scripts/mysql_setup.sql.example](C:/Users/diyav/OneDrive/Documents/assignment/scripts/mysql_setup.sql.example). Replace placeholder passwords before running it locally.

The script creates:

- `pharmaq_sentinel`
- `pharmaq_sentinel_test`

Both databases use `utf8mb4` character encoding and `utf8mb4_0900_ai_ci` collation.

## 4. Create Users

Create one local application user and one local test user. Use different passwords for each.

Use placeholders such as `CHANGE_THIS_LOCAL_PASSWORD` only in example files. Do not commit real passwords.

## 5. Copy Environment File

From the repository root:

```powershell
Copy-Item .env.example .env
```

Edit `.env` so `DATABASE_URL`, `TEST_DATABASE_URL`, `MYSQL_USER`, and `MYSQL_PASSWORD` match your local MySQL setup.

## 6. Test The Connection

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts\check_database.py
```

Expected result when MySQL is available:

```text
MySQL connection status: connected
```

If MySQL is unavailable, the FastAPI app still starts and `/health` reports a degraded status.

## 7. Common Errors

Access denied:

- Confirm the username and password in `.env`.
- Confirm grants were applied to the expected database.
- Confirm the user host is `localhost` or `%` according to your setup.

Connection refused:

- Confirm the MySQL service is running.
- Confirm `MYSQL_PORT` is `3306` unless your installation uses a custom port.
- Confirm firewall rules are not blocking localhost connections.

Unknown database:

- Run the setup SQL.
- Confirm the database name matches `MYSQL_DATABASE`.
