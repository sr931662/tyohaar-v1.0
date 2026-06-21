"""
Auth domain — internal / admin schemas.

These schemas are ORM-mapped and INCLUDE sensitive fields that must
never appear in public-facing API responses:
  - OTPInternal    → otp_hash, device_fingerprint, failure_log
  - SessionInternal → session_token, access_jti, push_notification_token
  - RefreshTokenInternal → token_hash, reuse_detected_at, reuse_ip_address

Usage:
  - Admin dashboards and internal tooling only.
  - Service-to-service communication where full context is required.
  - MUST NOT be used as the response_model in public FastAPI routes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from app.models.enums import (
    DeviceType,
    LoginMethod,
    OTPDeliveryChannel,
    OTPPurpose,
    OTPStatus,
    Platform,
    SessionStatus,
    TokenRevocationReason,
)
from app.schemas.base import BaseSchema, IDSchema, TimestampSchema

__all__ = [
    "OTPInternal",
    "SessionInternal",
    "RefreshTokenInternal",
]


class OTPInternal(IDSchema, TimestampSchema):
    """
    Full internal representation of an OTPRecord.

    SENSITIVE — contains otp_hash, device_fingerprint, failure_log.
    Restricted to admin/fraud analysis endpoints.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID | None = Field(
        default=None,
        description="NULL for pre-registration OTPs issued before a user row exists.",
    )
    identifier: str = Field(max_length=320)
    channel: OTPDeliveryChannel
    purpose: OTPPurpose
    status: OTPStatus

    # ── SENSITIVE ──────────────────────────────────────────────────────────────
    otp_hash: str = Field(
        description="HMAC-SHA256 hash of the raw OTP. NEVER log or expose publicly."
    )
    device_fingerprint: str | None = Field(
        default=None,
        description="Client device fingerprint. NEVER expose publicly.",
    )
    failure_log: dict[str, Any] | None = Field(
        default=None,
        description="JSONB audit log of verification failures. NEVER expose publicly.",
    )
    # ──────────────────────────────────────────────────────────────────────────

    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    resend_count: int = Field(ge=0)
    max_resends: int = Field(ge=1)
    expires_at: datetime
    verified_at: datetime | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = None
    failure_reason: str | None = None
    delivered_at: datetime | None = None
    delivery_reference: str | None = None


class SessionInternal(IDSchema, TimestampSchema):
    """
    Full internal representation of a UserSession.

    SENSITIVE — contains session_token, access_jti, push_notification_token.
    Restricted to token refresh services and admin tooling.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID

    # ── SENSITIVE ──────────────────────────────────────────────────────────────
    session_token: str = Field(
        max_length=128,
        description="Raw session token. NEVER expose in public API responses.",
    )
    access_jti: str = Field(
        max_length=128,
        description="JWT ID of the associated access token. NEVER expose publicly.",
    )
    push_notification_token: str | None = Field(
        default=None,
        description="FCM/APNs push token. NEVER expose publicly.",
    )
    # ──────────────────────────────────────────────────────────────────────────

    device_id: str | None = None
    device_name: str | None = None
    device_type: DeviceType | None = None
    platform: Platform | None = None
    os: str | None = None
    os_version: str | None = None
    browser: str | None = None
    browser_version: str | None = None
    app_version: str | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    country_code: str | None = Field(default=None, max_length=2)
    region: str | None = None
    city: str | None = None
    timezone: str | None = None
    language: str | None = None
    login_method: LoginMethod | None = None
    status: SessionStatus
    login_at: datetime
    last_activity_at: datetime | None = None
    logout_at: datetime | None = None
    expires_at: datetime
    remember_me: bool
    is_trusted: bool
    is_active: bool
    is_revoked: bool
    revoked_at: datetime | None = None
    revocation_reason: str | None = None
    user_agent: str | None = None


class RefreshTokenInternal(IDSchema, TimestampSchema):
    """
    Full internal representation of a RefreshToken.

    SENSITIVE — contains token_hash, reuse_detected_at, reuse_ip_address.
    Restricted to the token rotation service and security audit endpoints.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    jti: str = Field(max_length=128)
    user_id: uuid.UUID
    session_id: uuid.UUID
    family_id: uuid.UUID
    parent_jti: str | None = Field(default=None, max_length=128)

    # ── SENSITIVE ──────────────────────────────────────────────────────────────
    token_hash: str = Field(
        description="SHA-256 hash of the raw refresh token. NEVER expose publicly."
    )
    reuse_detected_at: datetime | None = Field(
        default=None,
        description=(
            "UTC timestamp when token reuse was detected (possible theft). "
            "INTERNAL security field — NEVER expose publicly."
        ),
    )
    reuse_ip_address: str | None = Field(
        default=None,
        max_length=45,
        description=(
            "IP from which the reused token was presented. "
            "INTERNAL security field — NEVER expose publicly."
        ),
    )
    # ──────────────────────────────────────────────────────────────────────────

    device_id: str | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    issued_at: datetime
    expires_at: datetime
    is_used: bool
    used_at: datetime | None = None
    is_revoked: bool
    revoked_at: datetime | None = None
    revocation_reason: TokenRevocationReason | None = None
