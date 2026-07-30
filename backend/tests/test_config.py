import pytest
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.main import create_app


def test_configuration_loading() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "PharmaQ Sentinel"
    assert settings.app_version == "0.1.0"
    assert settings.llm_provider == "openai"
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


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValueError, match="Wildcard CORS"):
        Settings(_env_file=None, BACKEND_CORS_ORIGINS="*")


def test_cors_configuration() -> None:
    app = create_app()

    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_origins"] == ["http://localhost:5173"]
    assert cors_middleware.kwargs["allow_credentials"] is True
