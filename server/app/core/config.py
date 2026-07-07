from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


def _parse_list_env(v: str) -> list[str]:
    """Accept comma-separated string or JSON array from an environment variable."""
    v = v.strip()
    if v.startswith("["):
        import json
        return json.loads(v)
    return [item.strip() for item in v.split(",") if item.strip()]


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

    # ── CORS / Trusted Hosts ──────────────────────────────────────────────────
    # Stored as raw strings (not list[str]) deliberately: pydantic-settings
    # attempts to JSON-decode any list-typed field's raw env value *before*
    # field validators run, so a plain comma-separated string — our documented
    # format — would fail at the settings-source level with a
    # JSONDecodeError, never reaching a `mode="before"` validator. Parsing
    # into a list ourselves via the properties below sidesteps that entirely.
    ALLOWED_ORIGINS_RAW: str = Field(default="*", alias="ALLOWED_ORIGINS")
    # Set to specific hostnames in production, e.g. tyohaar.co,www.tyohaar.co
    ALLOWED_HOSTS_RAW: str = Field(default="*", alias="ALLOWED_HOSTS")

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:  # noqa: N802
        return _parse_list_env(self.ALLOWED_ORIGINS_RAW)

    @property
    def ALLOWED_HOSTS(self) -> list[str]:  # noqa: N802
        return _parse_list_env(self.ALLOWED_HOSTS_RAW)

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

    # ── OAuth ────────────────────────────────────────────────────────────────
    # Google Cloud Console → APIs & Services → Credentials → OAuth Client ID (Web).
    # Leave blank in dev; Google Sign-In endpoints return a clear error until set.
    GOOGLE_CLIENT_ID: str = ""

    # ── Image Storage (Cloudinary) ──────────────────────────────────────────
    # cloudinary.com → Dashboard → Product Environment Credentials.
    # Leave blank in dev; the image upload endpoint returns a clear error until set.
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ── Payment Gateway (Razorpay) ───────────────────────────────────────────
    # dashboard.razorpay.com → Settings → API Keys, for RAZORPAY_KEY_ID/SECRET.
    # dashboard.razorpay.com → Settings → Webhooks, for RAZORPAY_WEBHOOK_SECRET
    # (set when creating the webhook endpoint — a separate secret from the API keys).
    # Leave blank in dev; payment initiation/webhook endpoints return a clear
    # error until set. Never log or expose RAZORPAY_KEY_SECRET/WEBHOOK_SECRET.
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

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
