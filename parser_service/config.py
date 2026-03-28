from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent


class ParserServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Обязательный ключ для всех вызовов /v1/* (кроме /health)
    parser_service_api_key: str = Field(default="", validation_alias="PARSER_SERVICE_API_KEY")

    parser_mode: str = Field(default="mock", validation_alias="PARSER_MODE")

    bind_host: str = Field(default="127.0.0.1", validation_alias="PARSER_BIND_HOST")
    bind_port: int = Field(default=8810, validation_alias="PARSER_BIND_PORT")


def get_parser_settings() -> ParserServiceSettings:
    return ParserServiceSettings()
