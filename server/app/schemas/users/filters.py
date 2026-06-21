"""
Users domain — query-parameter filter schemas.

Used by list endpoints to build WHERE clauses via the repository layer.
All fields are Optional so any combination can be omitted.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.models.enums import (
    AccountStatus,
    AddressType,
    DeviceType,
    Platform,
    UserRole,
    UserType,
    VerificationStatus,
)
from app.schemas.base import BaseSchema

__all__ = [
    "UserFilters",
    "UserAddressFilters",
    "UserDeviceFilters",
]


class UserFilters(BaseSchema):
    """
    Query filters for the User list endpoint.

    `search` performs a case-insensitive ILIKE against full_name, username,
    phone, and email columns. Date filters apply to the `created_at` column.
    """

    model_config = ConfigDict(populate_by_name=True)

    role: UserRole | None = Field(
        default=None,
        description="Filter by user authorization role.",
    )
    user_type: UserType | None = Field(
        default=None,
        description="Filter by account type (INDIVIDUAL / BUSINESS).",
    )
    account_status: AccountStatus | None = Field(
        default=None,
        description="Filter by account lifecycle status.",
    )
    verification_status: VerificationStatus | None = Field(
        default=None,
        description="Filter by identity verification status.",
    )
    phone_verified: bool | None = Field(
        default=None,
        description="True → only phone-verified users; False → unverified.",
    )
    email_verified: bool | None = Field(
        default=None,
        description="True → only email-verified users; False → unverified.",
    )
    mfa_enabled: bool | None = Field(
        default=None,
        description="Filter by MFA enrollment status.",
    )
    search: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description=(
            "Case-insensitive search against full_name, username, "
            "phone, and email columns."
        ),
    )
    city: str | None = Field(
        default=None,
        max_length=100,
        description="Filter by city in the user's profile.",
    )
    state: str | None = Field(
        default=None,
        max_length=100,
        description="Filter by state in the user's profile.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Return users with created_at ≥ this UTC datetime.",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Return users with created_at ≤ this UTC datetime.",
    )


class UserAddressFilters(BaseSchema):
    """
    Query filters for the UserAddress list endpoint.

    Can be used to find all addresses for a user, or to locate addresses
    by geographic hierarchy for delivery routing.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Return addresses belonging to this user only.",
    )
    address_type: AddressType | None = Field(
        default=None,
        description="Filter by address category.",
    )
    is_default: bool | None = Field(
        default=None,
        description="True → only the default address; False → non-default.",
    )
    is_active: bool | None = Field(
        default=None,
        description="True → only active addresses; False → inactive.",
    )
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=10)


class UserDeviceFilters(BaseSchema):
    """
    Query filters for the UserDevice list endpoint.

    Useful for push notification targeting and security audits.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Return devices belonging to this user only.",
    )
    device_type: DeviceType | None = Field(
        default=None,
        description="Filter by device form factor.",
    )
    platform: Platform | None = Field(
        default=None,
        description="Filter by OS platform.",
    )
    is_trusted: bool | None = Field(
        default=None,
        description="True → only trusted devices; False → untrusted.",
    )
    is_active: bool | None = Field(
        default=None,
        description="True → only active devices; False → deactivated.",
    )
