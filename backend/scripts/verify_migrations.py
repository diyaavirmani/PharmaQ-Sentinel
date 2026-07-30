from __future__ import annotations

import os
from pathlib import Path

from alembic.config import Config
from sqlalchemy.engine import make_url

from alembic import command
from app.core.config import get_settings


def safe_test_url() -> str:
    settings = get_settings()
    url = make_url(settings.test_database_url.get_secret_value())
    if url.drivername != "mysql+pymysql":
        raise RuntimeError("TEST_DATABASE_URL must use mysql+pymysql")
    if not url.database or not url.database.endswith("_test"):
        raise RuntimeError("Refusing migration verification: database name must end in _test")
    print(f"Verifying migrations against MySQL test database: {url.database}")
    print(f"Connection: {url.render_as_string(hide_password=True)}")
    return url.render_as_string(hide_password=False)


def alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[1]
    return Config(str(backend_dir / "alembic.ini"))


def main() -> None:
    os.environ["DATABASE_URL"] = safe_test_url()
    get_settings.cache_clear()
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.current(config)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    print("Migration upgrade/downgrade verification completed.")


if __name__ == "__main__":
    main()
