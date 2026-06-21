"""
Users domain — public GET response schemas.

These schemas are ORM-mapped (from_attributes=True) and intentionally
omit every field in the security exclusion list:
  - failed_login_count, account_locked_until
  - password_last_changed_at, last_password_reset_at
  - deleted_at, is_deleted
  - extra_metadata (UserProfile)
  - push_notification_token (UserDevice)

`UserResponse.display_name` is a Pydantic computed_field derived from
the user's name fields at serialization time.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, computed_field, field_serializer

from app.models.enums import (
    AccountStatus,
    AddressType,
    Currency,
    DeviceType,
    Gender,
    Language,
    LoginMethod,
    Platform,
    UserRole,
    UserType,
    VerificationStatus,
)
from app.schemas.base import BaseSchema, IDSchema, Latitude, Longitude, TimestampSchema

__all__ = [
    "UserResponse",
    "UserPublicResponse",
    "UserProfileResponse",
    "UserAddressResponse",
    "UserDeviceResponse",
]


class UserResponse(IDSchema, TimestampSchema):
    """
    Standard read representation of a User account.

    Returned by `GET /users/{id}` and embedded in most domain responses.
    Sensitive security fields (failed_login_count, account_locked_until,
    password_last_changed_at, last_password_reset_at, deleted_at) are
    strictly excluded.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    phone: str = Field(description="Primary phone number in E.164 format.")
    email: str | None = None
    username: str | None = None
    full_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    role: UserRole
    user_type: UserType
    account_status: AccountStatus
    verification_status: VerificationStatus
    primary_login_provider: LoginMethod | None = None
    phone_verified: bool
    email_verified: bool
    last_login_at: datetime | None = None
    mfa_enabled: bool

    @computed_field(description="Best available display name for the user.")
    @property
    def display_name(self) -> str:
        """
        Derives a human-readable display name using the priority chain:
          full_name → first+last → username → masked phone
        """
        if self.full_name:
            return self.full_name
        parts = [p for p in (self.first_name, self.last_name) if p]
        if parts:
            return " ".join(parts)
        if self.username:
            return self.username
        # Mask the phone: show country code + last 4 digits
        if len(self.phone) >= 4:
            return f"{self.phone[:3]}****{self.phone[-4:]}"
        return self.phone


class UserPublicResponse(BaseSchema):
    """
    Minimal public profile for social / discovery contexts.

    Returned when one user views another user's profile (e.g. in a
    vendor listing or guest invitation). Only CUSTOMER and VENDOR roles
    are surfaced; staff roles are hidden.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    username: str | None = None
    full_name: str | None = None
    role: UserRole | None = Field(
        default=None,
        description="Only CUSTOMER or VENDOR; SUPPORT/ADMIN/SUPER_ADMIN are masked.",
    )
    profile_photo_url: str | None = Field(
        default=None,
        description="CDN URL for the user's avatar. Sourced from the UserProfile.",
    )

    @computed_field(description="Resolved public display name.")
    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        if self.username:
            return self.username
        return str(self.id)[:8]

    @field_serializer("role")
    def mask_staff_role(self, role: UserRole | None) -> str | None:
        """Hide internal staff roles from public responses."""
        if role in (UserRole.SUPPORT, UserRole.ADMIN, UserRole.SUPER_ADMIN):
            return None
        return role.value if role else None


class UserProfileResponse(IDSchema, TimestampSchema):
    """
    Public read representation of a UserProfile.

    `extra_metadata` is excluded. `emergency_contact_phone` is also
    excluded from the public response (partially sensitive); it is
    available only in UserProfileInternal for admin use.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID = Field(description="UUID of the owning user.")

    # Media
    profile_photo_url: str | None = None
    cover_image_url: str | None = None

    # Personal details
    gender: Gender | None = None
    date_of_birth: date | None = None
    anniversary_date: date | None = None
    occupation: str | None = None
    bio: str | None = None

    # Localisation
    preferred_language: Language
    timezone: str
    preferred_currency: Currency

    # Location
    city: str | None = None
    state: str | None = None
    country: str | None = None
    pincode: str | None = None

    # Emergency contact (name + relation only; phone excluded from public view)
    emergency_contact_name: str | None = None
    emergency_contact_relation: str | None = None


class UserAddressResponse(IDSchema, TimestampSchema):
    """
    Read representation of a UserAddress.

    Includes latitude/longitude for map rendering. `deleted_at` and
    `is_deleted` are excluded; soft-deleted addresses are simply
    filtered out at the repository layer.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID
    address_type: AddressType
    label: str | None = None
    recipient_name: str | None = None
    recipient_phone: str | None = None
    alternate_phone: str | None = None
    address_line_1: str
    address_line_2: str | None = None
    landmark: str | None = None
    locality: str | None = None
    city: str
    district: str | None = None
    state: str
    country: str
    postal_code: str
    latitude: Latitude = None
    longitude: Longitude = None
    delivery_instructions: str | None = None
    is_default: bool
    is_active: bool


class UserDeviceResponse(IDSchema, TimestampSchema):
    """
    Public read representation of a UserDevice.

    `push_notification_token` is strictly excluded. `is_rooted` is
    included so the client can display a security warning in the device
    list UI.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID
    device_id: str
    device_type: DeviceType
    platform: Platform
    manufacturer: str | None = None
    model: str | None = None
    os: str | None = None
    os_version: str | None = None
    app_version: str | None = None
    timezone: str | None = None
    language: str | None = None
    last_active_at: datetime | None = None
    is_trusted: bool
    is_active: bool
    is_rooted: bool | None = Field(
        default=None,
        description="True if the device appears to be rooted/jailbroken.",
    )
