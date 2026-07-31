import pytest
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, normalise_mysql_sqlalchemy_url, redact_database_url
from app.main import create_app


def test_configuration_loading() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "PharmaQ Sentinel"
    assert settings.app_version == "0.1.0"
    assert settings.llm_provider == "openai"
    assert settings.demo_ai_mode == "live"
    assert settings.database_url_value().startswith("mysql+pymysql://")


def test_secret_values_not_present_in_serialised_settings() -> None:
    settings = Settings(
        _env_file=None,
        MYSQL_PASSWORD="super-secret-db-password",
        DATABASE_URL="mysql+pymysql://pharmaq_user:super-secret-db-password@127.0.0.1:3306/pharmaq_sentinel?charset=utf8mb4",
        OPENAI_API_KEY="sk-test-secret",
    )

    serialised = str(settings.public_safe_dict())

    assert "super-secret-db-password" not in serialised
    assert "sk-test-secret" not in serialised
    assert "DATABASE_URL" not in serialised


def test_database_url_takes_precedence_over_mysql_url() -> None:
    settings = Settings(
        _env_file=None,
        DATABASE_URL="mysql+pymysql://database_user:database-password@127.0.0.1:3306/from_database?charset=utf8mb4",
        MYSQL_URL="mysql://mysql_user:mysql-password@railway.internal:3306/from_mysql",
    )

    selected_url = settings.database_url_value()

    assert "from_database" in selected_url
    assert "database_user" in selected_url
    assert "from_mysql" not in selected_url


def test_mysql_url_is_used_when_database_url_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(
        _env_file=None,
        MYSQL_URL="mysql://railway_user:railway-password@railway.internal:3306/railway",
    )

    assert settings.database_url_value() == (
        "mysql+pymysql://railway_user:railway-password@railway.internal:3306/railway"
    )


def test_mysql_prefix_is_normalised_once_for_sqlalchemy() -> None:
    normalised = normalise_mysql_sqlalchemy_url(
        "mysql://user:password@127.0.0.1:3306/pharmaq?note=mysql://leave-this-alone"
    )

    assert normalised.startswith("mysql+pymysql://")
    assert normalised.endswith("note=mysql://leave-this-alone")
    assert normalised.count("mysql+pymysql://") == 1


def test_database_url_redaction_hides_credentials() -> None:
    redacted = redact_database_url(
        "mysql://pharmaq_user:very-secret-password@containers-us-west.railway.app:3306/railway"
    )

    assert redacted == "mysql+pymysql://pharmaq_user:***@containers-us-west.railway.app:3306/railway"
    assert "very-secret-password" not in redacted


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValueError, match="Wildcard CORS"):
        Settings(_env_file=None, BACKEND_CORS_ORIGINS="*")


def test_demo_ai_mode_is_validated() -> None:
    assert Settings(_env_file=None, DEMO_AI_MODE="deterministic").demo_ai_mode == "deterministic"
    with pytest.raises(ValueError, match="DEMO_AI_MODE"):
        Settings(_env_file=None, DEMO_AI_MODE="random")


def test_cors_configuration() -> None:
    app = create_app()

    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_origins"] == ["http://localhost:5173"]
    assert cors_middleware.kwargs["allow_credentials"] is True
