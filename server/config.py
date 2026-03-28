from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    app_base_url: str = Field(default="", validation_alias="APP_BASE_URL")

    db_host: str = Field(default="127.0.0.1", validation_alias="DB_HOST")
    db_port: int = Field(default=3306, validation_alias="DB_PORT")
    pi_db_name: str = Field(default="vtb_price_intel", validation_alias="PI_DB_NAME")
    db_user: str = Field(default="", validation_alias="DB_USER")
    db_password: str = Field(default="", validation_alias="DB_PASSWORD")
    db_socket: str | None = Field(default=None, validation_alias="DB_SOCKET")

    admin_username: str = Field(default="admin", validation_alias="ADMIN_USERNAME")
    admin_password: str = Field(default="", validation_alias="ADMIN_PASSWORD")

    parser_mode: str = Field(default="mock", validation_alias="PARSER_MODE")

    # Внешний микросервис парсера (если задан — сценарии ходят в HTTP API вместо локального mock)
    parser_service_url: str = Field(default="", validation_alias="PARSER_SERVICE_URL")
    parser_service_api_key: str = Field(default="", validation_alias="PARSER_SERVICE_API_KEY")
    parser_service_timeout: float = Field(default=120.0, validation_alias="PARSER_SERVICE_TIMEOUT")

    @property
    def project_root(self) -> Path:
        return _ROOT


def get_settings() -> Settings:
    return Settings()
