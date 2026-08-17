from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AIMode(StrEnum):
    EMBEDDED = "embedded"
    REMOTE = "remote"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    port: int = 8000
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    database_url: str | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 10

    ai_mode: AIMode = AIMode.EMBEDDED
    ai_server_endpoint: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    ai_timeout_seconds: float = 30.0
    ai_max_retries: int = 2

    device_api_keys: Annotated[list[str], NoDecode] = []
    upload_rate_limit_per_minute: int = 120

    audio_sample_rate: int = 16_000
    audio_sample_width: int = 4
    audio_channels: int = 1
    audio_leq_period_seconds: int = 20
    audio_max_chunk_bytes: int = 1_280_000
    audio_max_buffer_bytes: int = 2_560_000
    audio_buffer_ttl_seconds: int = 300
    audio_max_active_sessions: int = 100
    audio_gain: float = 1.0

    @field_validator("cors_origins", "device_api_keys", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str | None) -> str | None:
        if value and not value.startswith(("postgresql+psycopg://", "postgresql+psycopg_async://")):
            raise ValueError("DATABASE_URL must use SQLAlchemy's psycopg 3 PostgreSQL dialect")
        return value

    @property
    def audio_window_bytes(self) -> int:
        return (
            self.audio_sample_rate
            * self.audio_sample_width
            * self.audio_leq_period_seconds
        )

    @property
    def samples_per_leq(self) -> int:
        return self.audio_sample_rate * self.audio_leq_period_seconds


@lru_cache
def get_settings() -> Settings:
    return Settings()
