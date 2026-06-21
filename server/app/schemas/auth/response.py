"""
Auth domain — public GET response schemas.

These schemas are ORM-mapped (from_attributes=True) and intentionally
omit every field listed in the security exclusion list:
  - otp_hash, token_hash, session_token, access_jti, gateway_signature
  - device_fingerprint, push_notification_token
  - internal_notes, extra_metadata
  - deleted_at, is_deleted
  - failed_login_count, account_locked_until, password_last_changed_at
  - reuse_detected_at, reuse_ip_address (refresh token internals)
  - failure_log (OTP internal audit)
"""

from __future__ import annotations

import uuid
from datetime import datetime

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
    "OTPSentResponse",
    "OTPVerifyResponse",
    "SessionResponse",
    "RefreshTokenResponse",
]


class OTPSentResponse(BaseSchema):
    """
    Response body for `POST /auth/otp/request`.

    Confirms dispatch; includes metadata needed for the client to manage
    resend-rate-limiting and attempt countdown UX.
    Sensitive fields (otp_hash, device_fingerprint, failure_log) are
    strictly excluded.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    status: OTPStatus = Field(description="Current lifecycle state of the OTP record.")
    channel: OTPDeliveryChannel = Field(
        description="Channel through which the OTP was dispatched."
    )
    expires_at: datetime = Field(
        description="UTC datetime after which the OTP is no longer valid."
    )
    resend_count: int = Field(
        ge=0,
        description="Number of times the OTP has been resent so far.",
    )
    max_resends: int = Field(
        ge=1,
        description="Maximum number of resend attempts allowed.",
    )
    attempt_count: int = Field(
        ge=0,
        description="Number of verification attempts made so far.",
    )
    max_attempts: int = Field(
        ge=1,
        description="Maximum number of verification attempts allowed.",
    )
    delivered_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the gateway confirmed delivery.",
    )
    delivery_reference: str | None = Field(
        default=None,
        description="Opaque delivery reference returned by the SMS/email gateway.",
    )


class OTPVerifyResponse(BaseSchema):
    """
    Response body for `POST /auth/otp/verify`.

    Confirms whether the submitted OTP code was accepted.
    The upstream auth handler may issue access/refresh tokens in addition
    to returning this payload.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    identifier: str = Field(
        description="The phone or email against which verification was performed."
    )
    purpose: OTPPurpose = Field(description="The purpose scope of the verified OTP.")
    status: OTPStatus = Field(
        description="VERIFIED on success; EXHAUSTED or EXPIRED on failure."
    )
    verified_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of successful verification, if applicable.",
    )
    failure_reason: str | None = Field(
        default=None,
        description="Human-readable failure reason when status is not VERIFIED.",
    )


class SessionResponse(IDSchema, TimestampSchema):
    """
    Public read representation of a UserSession.

    Includes device and geo context so clients can show the user their
    active sessions in a security dashboard. Sensitive tokens
    (session_token, access_jti, push_notification_token) are strictly
    excluded.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID = Field(description="UUID of the owning user.")

    # Device context
    device_id: str | None = None
    device_name: str | None = None
    device_type: DeviceType | None = None
    platform: Platform | None = None
    os: str | None = None
    os_version: str | None = None
    browser: str | None = None
    browser_version: str | None = None
    app_version: str | None = None
    user_agent: str | None = None

    # Network / geo context
    ip_address: str | None = Field(default=None, max_length=45)
    country_code: str | None = Field(default=None, max_length=2)
    region: str | None = None
    city: str | None = None
    timezone: str | None = None
    language: str | None = None

    # Auth context
    login_method: LoginMethod | None = None
    status: SessionStatus = Field(description="Current lifecycle state of the session.")
    login_at: datetime = Field(description="UTC timestamp when the session was created.")
    last_activity_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of the most recent authenticated request.",
    )
    logout_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the user explicitly logged out.",
    )
    expires_at: datetime = Field(
        description="UTC timestamp when the session token expires."
    )

    # Session flags
    remember_me: bool = Field(
        description="True if a long-lived session was requested."
    )
    is_trusted: bool = Field(
        description="True if this device has been marked as trusted by the user."
    )
    is_active: bool = Field(description="False once the session has been terminated.")
    is_revoked: bool = Field(
        description="True if the session was revoked by admin or security event."
    )
    revoked_at: datetime | None = None
    revocation_reason: str | None = None


class RefreshTokenResponse(IDSchema, TimestampSchema):
    """
    Public read representation of a RefreshToken.

    Used by admin dashboards and audit endpoints to inspect token
    rotation history. The raw token hash and reuse-detection fields
    are strictly excluded.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID = Field(description="UUID of the owning user.")
    session_id: uuid.UUID = Field(description="UUID of the parent session.")
    family_id: uuid.UUID = Field(
        description="Rotation family UUID; shared by all tokens in a chain."
    )
    jti: str = Field(
        max_length=128,
        description="JWT ID of this refresh token.",
    )
    parent_jti: str | None = Field(
        default=None,
        description="JTI of the preceding token in the rotation chain.",
    )
    device_id: str | None = None
    ip_address: str | None = Field(default=None, max_length=45)
    issued_at: datetime = Field(description="UTC timestamp when the token was issued.")
    expires_at: datetime = Field(description="UTC timestamp when the token expires.")
    is_used: bool = Field(
        description="True once the token has been exchanged for a new pair."
    )
    used_at: datetime | None = None
    is_revoked: bool = Field(description="True if the token was explicitly revoked.")
    revoked_at: datetime | None = None
    revocation_reason: TokenRevocationReason | None = None
