"""
Auth domain — POST request body schemas (Create).

These schemas validate inbound data from API consumers.
They are NOT ORM-mapped; `from_attributes` is intentionally absent.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    DeviceType,
    LoginMethod,
    OTPDeliveryChannel,
    OTPPurpose,
    Platform,
)
from app.schemas.base import BaseSchema
from app.schemas.auth.common import (
    DeviceInfoSchema,
    LocationInfoSchema,
    OTPCode,
    OTPIdentifier,
    validate_otp_identifier,
)

__all__ = [
    "OTPRequestCreate",
    "OTPVerifyCreate",
    "SessionCreate",
    "RefreshTokenCreate",
]


class OTPRequestCreate(BaseSchema):
    """
    Request body for `POST /auth/otp/request`.

    Triggers OTP generation and dispatch to the given identifier.
    `device_fingerprint` is consumed by the service layer only and
    must never be echoed back in API responses.
    """

    model_config = ConfigDict(populate_by_name=True)

    identifier: OTPIdentifier = Field(
        description="Phone (E.164) or email to which the OTP is sent."
    )
    channel: OTPDeliveryChannel = Field(
        description="Delivery channel: SMS, EMAIL, WHATSAPP, or VOICE."
    )
    purpose: OTPPurpose = Field(
        description="Declared purpose that scopes this OTP to one action."
    )
    device_fingerprint: str | None = Field(
        default=None,
        max_length=512,
        description=(
            "Client-side device fingerprint. "
            "Stored internally for fraud detection; never returned in responses."
        ),
    )

    @field_validator("identifier", mode="before")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        return validate_otp_identifier(v)


class OTPVerifyCreate(BaseSchema):
    """
    Request body for `POST /auth/otp/verify`.

    Submits the OTP code the user received so the service layer can
    compare it against the stored HMAC hash.
    """

    model_config = ConfigDict(populate_by_name=True)

    identifier: OTPIdentifier = Field(
        description="The same phone or email that was used in OTPRequestCreate."
    )
    otp_code: OTPCode = Field(
        description="Numeric OTP code (4–8 digits) entered by the user."
    )
    purpose: OTPPurpose = Field(
        description="Must match the purpose declared in OTPRequestCreate."
    )

    @field_validator("identifier", mode="before")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        return validate_otp_identifier(v)


class SessionCreate(BaseSchema):
    """
    Internal service schema for creating a new UserSession row.

    Called by the auth service after a successful OTP verification or
    OAuth flow. Clients never POST this directly.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID = Field(description="UUID of the authenticated user.")
    login_method: LoginMethod = Field(
        description="Authentication mechanism that produced this session."
    )

    # Device context (flattened from DeviceInfoSchema for direct ORM mapping)
    device_id: str | None = Field(default=None, max_length=256)
    device_name: str | None = Field(default=None, max_length=200)
    device_type: DeviceType | None = None
    platform: Platform | None = None
    os: str | None = Field(default=None, max_length=50)
    os_version: str | None = Field(default=None, max_length=50)
    browser: str | None = Field(default=None, max_length=100)
    browser_version: str | None = Field(default=None, max_length=100)
    app_version: str | None = Field(default=None, max_length=50)
    user_agent: str | None = Field(default=None, max_length=512)

    # Network / geo context
    ip_address: str | None = Field(default=None, max_length=45)
    country_code: str | None = Field(default=None, max_length=2)
    region: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=20)

    # Session preferences
    remember_me: bool = Field(
        default=False,
        description="If True, a longer-lived session/token pair is issued.",
    )

    # Push notification token (service-layer only, never returned)
    push_notification_token: str | None = Field(
        default=None,
        description=(
            "FCM/APNs push token. Stored internally; never returned in responses."
        ),
    )


class RefreshTokenCreate(BaseSchema):
    """
    Internal service schema for creating a new RefreshToken row.

    Issued by the token rotation service; never directly consumed by
    API clients.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID = Field(description="Owning user UUID.")
    session_id: uuid.UUID = Field(description="Parent session UUID.")
    family_id: uuid.UUID = Field(
        description=(
            "Token family UUID. All tokens in a rotation chain share the "
            "same family_id so that reuse detection can revoke the entire chain."
        )
    )
    parent_jti: str | None = Field(
        default=None,
        max_length=128,
        description="JTI of the immediately preceding token in the rotation chain.",
    )
    device_id: str | None = Field(default=None, max_length=256)
    ip_address: str | None = Field(default=None, max_length=45)
    issued_at: datetime = Field(description="UTC timestamp when the token was issued.")
    expires_at: datetime = Field(description="UTC timestamp when the token expires.")

    @model_validator(mode="after")
    def validate_expiry_after_issue(self) -> "RefreshTokenCreate":
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at.")
        return self
