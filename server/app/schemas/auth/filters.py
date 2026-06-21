"""
Auth domain — query-parameter filter schemas.

Used by list endpoints to build WHERE clauses via the repository layer.
All fields are Optional so any combination can be omitted.
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
)
from app.schemas.base import BaseSchema

__all__ = [
    "OTPFilters",
    "SessionFilters",
    "RefreshTokenFilters",
]


class OTPFilters(BaseSchema):
    """
    Query filters for the OTP records list endpoint.

    All fields are optional; omitted fields are treated as "no constraint".
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Filter to OTP records belonging to a specific user.",
    )
    identifier: str | None = Field(
        default=None,
        max_length=320,
        description="Exact match on phone or email identifier.",
    )
    channel: OTPDeliveryChannel | None = Field(
        default=None,
        description="Filter by delivery channel.",
    )
    purpose: OTPPurpose | None = Field(
        default=None,
        description="Filter by OTP purpose.",
    )
    status: OTPStatus | None = Field(
        default=None,
        description="Filter by lifecycle status.",
    )
    is_expired: bool | None = Field(
        default=None,
        description=(
            "True → only records where expires_at < now(); "
            "False → only non-expired records."
        ),
    )
    from_date: datetime | None = Field(
        default=None,
        description="Filter records created at or after this UTC datetime.",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Filter records created at or before this UTC datetime.",
    )


class SessionFilters(BaseSchema):
    """
    Query filters for the UserSession list endpoint.

    Supports date-range filtering on the `login_at` column.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Return sessions belonging to this user only.",
    )
    status: SessionStatus | None = Field(
        default=None,
        description="Filter by session lifecycle status.",
    )
    login_method: LoginMethod | None = Field(
        default=None,
        description="Filter by the authentication method used.",
    )
    device_type: DeviceType | None = Field(
        default=None,
        description="Filter by device form factor.",
    )
    platform: Platform | None = Field(
        default=None,
        description="Filter by OS platform.",
    )
    is_active: bool | None = Field(
        default=None,
        description="True → only active sessions; False → only inactive.",
    )
    is_revoked: bool | None = Field(
        default=None,
        description="True → only revoked sessions; False → only non-revoked.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Filter sessions with login_at ≥ this UTC datetime.",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Filter sessions with login_at ≤ this UTC datetime.",
    )


class RefreshTokenFilters(BaseSchema):
    """
    Query filters for the RefreshToken list endpoint.

    Useful for admin auditing of token rotation chains.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Return tokens belonging to this user only.",
    )
    session_id: uuid.UUID | None = Field(
        default=None,
        description="Return tokens within a specific session.",
    )
    family_id: uuid.UUID | None = Field(
        default=None,
        description="Return all tokens in a rotation family.",
    )
    is_used: bool | None = Field(
        default=None,
        description="True → only consumed tokens; False → only unconsumed.",
    )
    is_revoked: bool | None = Field(
        default=None,
        description="True → only revoked tokens; False → only active.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Filter tokens with issued_at ≥ this UTC datetime.",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Filter tokens with issued_at ≤ this UTC datetime.",
    )
