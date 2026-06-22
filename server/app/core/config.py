from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Tyohaar API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Security / JWT ───────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── Trusted Hosts ────────────────────────────────────────────────────────
    # Set to specific hostnames in production, e.g. ["api.tyohaar.com"].
    ALLOWED_HOSTS: list[str] = ["*"]

    @field_validator("ALLOWED_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_list_from_env(cls, v: object) -> object:
        """Accept comma-separated string or JSON array from environment variables."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # ── Pagination ───────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ── OTP ──────────────────────────────────────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_MAX_RESENDS: int = 3

    # ── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── Upload ───────────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == Environment.STAGING

    # ── Validators ───────────────────────────────────────────────────────────

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string "
                "(postgresql:// or postgresql+asyncpg://)."
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
