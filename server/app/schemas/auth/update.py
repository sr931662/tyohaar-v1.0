"""
Auth domain — PATCH request body schemas (Update).

All fields are Optional so callers send only the fields they wish to change.
These schemas are used by the service layer; they are not ORM-mapped.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from app.models.enums import SessionStatus, TokenRevocationReason
from app.schemas.base import BaseSchema

__all__ = [
    "SessionUpdate",
    "RefreshTokenUpdate",
]


class SessionUpdate(BaseSchema):
    """
    Partial update schema for a UserSession row.

    Used by the auth service to update session state during activity
    tracking, logout, or revocation events.
    """

    model_config = ConfigDict(populate_by_name=True)

    status: SessionStatus | None = Field(
        default=None,
        description="New lifecycle state for the session.",
    )
    last_activity_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent authenticated API call.",
    )
    is_active: bool | None = Field(
        default=None,
        description="Set to False to soft-deactivate the session.",
    )
    is_revoked: bool | None = Field(
        default=None,
        description="Set to True to mark the session as revoked.",
    )
    revoked_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the session was revoked.",
    )
    revocation_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Human-readable reason for session revocation.",
    )
    logout_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of the explicit logout event.",
    )
    push_notification_token: str | None = Field(
        default=None,
        description=(
            "Updated FCM/APNs push token. "
            "Stored internally; never returned in responses."
        ),
    )


class RefreshTokenUpdate(BaseSchema):
    """
    Partial update schema for a RefreshToken row.

    Used by the token rotation service after a refresh cycle and by the
    security service when token reuse is detected.
    Fields related to reuse detection (reuse_detected_at, reuse_ip_address)
    are present here for the service layer but must never appear in
    public-facing response schemas.
    """

    model_config = ConfigDict(populate_by_name=True)

    is_used: bool | None = Field(
        default=None,
        description="Mark the token as consumed after a successful refresh.",
    )
    used_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the token was consumed.",
    )
    is_revoked: bool | None = Field(
        default=None,
        description="Set to True to invalidate the token.",
    )
    revoked_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the token was revoked.",
    )
    revocation_reason: TokenRevocationReason | None = Field(
        default=None,
        description="Enumerated reason for token revocation.",
    )
    # Internal security fields — service/admin layer ONLY
    reuse_detected_at: datetime | None = Field(
        default=None,
        description=(
            "UTC timestamp when token reuse was detected. "
            "INTERNAL — must never be exposed in public API responses."
        ),
    )
    reuse_ip_address: str | None = Field(
        default=None,
        max_length=45,
        description=(
            "IP address from which the reused token was presented. "
            "INTERNAL — must never be exposed in public API responses."
        ),
    )
