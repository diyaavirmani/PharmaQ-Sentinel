# MySQL Migrations

Schema changes are managed with Alembic from the `backend/` directory. Alembic loads `DATABASE_URL` through `app.core.config`; credentials are not hardcoded in `alembic.ini`.

## Create Development Database

Use MySQL 8 or newer. Example local database names are placeholders:

```powershell
mysql -u root -p
```

```sql
CREATE DATABASE pharmaq_sentinel CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'pharmaq_user'@'localhost' IDENTIFIED BY 'replace_with_local_password';
GRANT ALL PRIVILEGES ON pharmaq_sentinel.* TO 'pharmaq_user'@'localhost';
FLUSH PRIVILEGES;
```

## Create Test Database

The test database name must end in `_test`. Tests refuse destructive setup otherwise.

```sql
CREATE DATABASE pharmaq_sentinel_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'pharmaq_test_user'@'localhost' IDENTIFIED BY 'replace_with_test_password';
GRANT ALL PRIVILEGES ON pharmaq_sentinel_test.* TO 'pharmaq_test_user'@'localhost';
FLUSH PRIVILEGES;
```

## Apply Migrations

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

## Check Status

```powershell
cd backend
alembic current
alembic history
```

## Generate Future Migrations

Inspect model changes first, then generate a migration:

```powershell
cd backend
alembic revision --autogenerate -m "describe change"
```

Review the generated migration before applying it. Do not accept generated PostgreSQL-specific types or oversized MySQL identifiers.

## Revert Latest Migration

```powershell
cd backend
alembic downgrade -1
```

Downgrades must not delete the database itself. They may drop tables or columns created by the migration when that is safe for the target environment.

## Verify Migration Round Trip

This command uses `TEST_DATABASE_URL`, refuses database names that do not end in `_test`, and performs a downgrade/upgrade round trip:

```powershell
cd backend
python scripts\verify_migrations.py
```

## Common PyMySQL Errors

- `Access denied`: check username, password, host, and grants.
- `Unknown database`: create the database first.
- `Can't connect to MySQL server`: start the MySQL service and confirm port `3306`.
- `Authentication plugin`: install `cryptography` and use a current PyMySQL version.
- `Specified key was too long`: reduce indexed `VARCHAR` length or constraint/index name length.
- `Cannot add foreign key constraint`: confirm referenced columns use compatible types, charset, and collation.
