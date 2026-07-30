from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    app_name: str = Field(default="PharmaQ Sentinel", validation_alias="APP_NAME")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    debug: bool = Field(default=True, validation_alias="DEBUG")

    backend_host: str = Field(default="127.0.0.1", validation_alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, validation_alias="BACKEND_PORT")
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        validation_alias="BACKEND_CORS_ORIGINS",
    )

    mysql_host: str = Field(default="127.0.0.1", validation_alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, validation_alias="MYSQL_PORT")
    mysql_database: str = Field(default="pharmaq_sentinel", validation_alias="MYSQL_DATABASE")
    mysql_user: str = Field(default="pharmaq_user", validation_alias="MYSQL_USER")
    mysql_password: SecretStr = Field(
        default=SecretStr("replace_with_local_password"),
        validation_alias="MYSQL_PASSWORD",
        repr=False,
        exclude=True,
    )

    database_url: SecretStr = Field(
        default=SecretStr(
            "mysql+pymysql://pharmaq_user:replace_with_local_password@127.0.0.1:3306/pharmaq_sentinel?charset=utf8mb4"
        ),
        validation_alias="DATABASE_URL",
        repr=False,
        exclude=True,
    )
    test_database_url: SecretStr = Field(
        default=SecretStr(
            "mysql+pymysql://pharmaq_test_user:replace_with_test_password@127.0.0.1:3306/pharmaq_sentinel_test?charset=utf8mb4"
        ),
        validation_alias="TEST_DATABASE_URL",
        repr=False,
        exclude=True,
    )

    database_pool_size: int = Field(default=5, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=5, validation_alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, validation_alias="DATABASE_POOL_TIMEOUT")
    database_pool_recycle_seconds: int = Field(
        default=1800,
        validation_alias="DATABASE_POOL_RECYCLE_SECONDS",
    )

    llm_provider: str = Field(default="openai", validation_alias="LLM_PROVIDER")
    openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="OPENAI_API_KEY",
        repr=False,
        exclude=True,
    )
    openai_model: str = Field(default="", validation_alias="OPENAI_MODEL")
    openai_timeout_seconds: int = Field(default=60, validation_alias="OPENAI_TIMEOUT_SECONDS")
    openai_max_retries: int = Field(default=2, validation_alias="OPENAI_MAX_RETRIES")
    enable_development_patch_endpoint: bool = Field(
        default=False,
        validation_alias="ENABLE_DEVELOPMENT_PATCH_ENDPOINT",
    )

    upload_directory: str = Field(default="backend/storage/uploads", validation_alias="UPLOAD_DIRECTORY")
    max_upload_size_mb: int = Field(default=10, validation_alias="MAX_UPLOAD_SIZE_MB")

    @computed_field
    @property
    def service_name(self) -> str:
        return "pharmaq-sentinel-api"

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value

        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("backend_cors_origins")
    @classmethod
    def reject_unrestricted_cors(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("Wildcard CORS origins are not allowed")

        return value

    @field_validator("database_url", "test_database_url")
    @classmethod
    def validate_mysql_url(cls, value: SecretStr) -> SecretStr:
        url = value.get_secret_value()
        if not url.startswith("mysql+pymysql://"):
            raise ValueError("Database URL must use mysql+pymysql")

        if "charset=utf8mb4" not in url:
            raise ValueError("Database URL must include charset=utf8mb4")

        return value

    def database_url_value(self) -> str:
        return self.database_url.get_secret_value()

    def public_safe_dict(self) -> dict[str, object]:
        return {
            "app_name": self.app_name,
            "app_env": self.app_env,
            "app_version": self.app_version,
            "debug": self.debug,
            "backend_host": self.backend_host,
            "backend_port": self.backend_port,
            "backend_cors_origins": self.backend_cors_origins,
            "llm_provider": self.llm_provider,
            "openai_model_configured": bool(self.openai_model),
            "development_patch_endpoint_enabled": self.enable_development_patch_endpoint,
            "upload_directory": self.upload_directory,
            "max_upload_size_mb": self.max_upload_size_mb,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
