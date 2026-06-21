"""
Users domain — PATCH request body schemas (Update).

All fields are Optional so callers send only the fields they wish to change.
Pydantic v2 will only validate fields that are explicitly provided.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    AddressType,
    Currency,
    DeviceType,
    Gender,
    Language,
    Platform,
    UserType,
)
from app.schemas.base import BaseSchema, Latitude, Longitude
from app.schemas.users.common import normalize_phone

__all__ = [
    "UserUpdate",
    "UserProfileUpdate",
    "UserAddressUpdate",
    "UserDeviceUpdate",
]


class UserUpdate(BaseSchema):
    """
    Partial update schema for the User model.

    Phone, role, and account/verification status are intentionally excluded:
      - phone changes require a dedicated OTP re-verification flow.
      - role/status changes are admin-only operations handled by separate endpoints.
    """

    model_config = ConfigDict(populate_by_name=True)

    email: str | None = Field(
        default=None,
        max_length=320,
        description="Updated email address. Triggers re-verification flow.",
    )
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        description="Updated unique handle. Alphanumeric, underscores, hyphens, dots.",
    )
    full_name: str | None = Field(default=None, max_length=200)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    user_type: UserType | None = Field(
        default=None,
        description="Change between INDIVIDUAL and BUSINESS account types.",
    )
    mfa_enabled: bool | None = Field(
        default=None,
        description="Toggle multi-factor authentication for this account.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip().lower()

    @field_validator("username", mode="before")
    @classmethod
    def normalise_username(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip().lower()


class UserProfileUpdate(BaseSchema):
    """
    Partial update schema for the UserProfile model.

    All profile fields are optional. `extra_metadata` is excluded — it
    is set only by the service layer, never directly by users.
    """

    model_config = ConfigDict(populate_by_name=True)

    profile_photo_url: str | None = Field(default=None, max_length=2048)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    gender: Gender | None = None
    date_of_birth: date | None = Field(
        default=None,
        description="Date of birth (YYYY-MM-DD).",
    )
    anniversary_date: date | None = None
    occupation: str | None = Field(default=None, max_length=200)
    bio: str | None = None
    religion: str | None = Field(default=None, max_length=100)
    preferred_language: Language | None = None
    timezone: str | None = Field(default=None, max_length=64)
    preferred_currency: Currency | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=10)
    alternate_phone: str | None = Field(default=None, max_length=15)
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(default=None, max_length=15)
    emergency_contact_relation: str | None = Field(default=None, max_length=100)

    @field_validator("alternate_phone", "emergency_contact_phone", mode="before")
    @classmethod
    def validate_optional_phone(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        return normalize_phone(v)

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_dob(cls, v: date | None) -> date | None:
        if v is None:
            return None
        from datetime import date as date_cls
        today = date_cls.today()
        if v >= today:
            raise ValueError("date_of_birth must be in the past.")
        return v


class UserAddressUpdate(BaseSchema):
    """
    Partial update schema for a UserAddress row.

    All fields optional. Coordinate fields (latitude/longitude) must be
    supplied together — see model_validator below.
    """

    model_config = ConfigDict(populate_by_name=True)

    address_type: AddressType | None = None
    label: str | None = Field(default=None, max_length=100)
    recipient_name: str | None = Field(default=None, max_length=200)
    recipient_phone: str | None = Field(default=None, max_length=15)
    alternate_phone: str | None = Field(default=None, max_length=15)
    address_line_1: str | None = Field(default=None, min_length=5, max_length=300)
    address_line_2: str | None = Field(default=None, max_length=300)
    landmark: str | None = Field(default=None, max_length=200)
    locality: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, min_length=1, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=10)
    latitude: Latitude = None
    longitude: Longitude = None
    delivery_instructions: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None

    @field_validator("recipient_phone", "alternate_phone", mode="before")
    @classmethod
    def validate_optional_phone(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        return normalize_phone(v)

    @model_validator(mode="after")
    def validate_coordinates_paired(self) -> "UserAddressUpdate":
        """Coordinates must be updated together or not at all."""
        has_lat = self.latitude is not None
        has_lng = self.longitude is not None
        if has_lat != has_lng:
            raise ValueError(
                "latitude and longitude must both be provided or both omitted."
            )
        return self


class UserDeviceUpdate(BaseSchema):
    """
    Partial update schema for a UserDevice row.

    Excludes device_id, device_type, platform, and hardware fields which
    are immutable after registration. The push_notification_token field
    is present for the push notification service but must never be
    returned in public API responses.
    """

    model_config = ConfigDict(populate_by_name=True)

    app_version: str | None = Field(
        default=None,
        max_length=50,
        description="Updated app version string from the client.",
    )
    push_notification_token: str | None = Field(
        default=None,
        description=(
            "Updated FCM/APNs token. "
            "Service-layer use only — never returned in public responses."
        ),
    )
    is_trusted: bool | None = Field(
        default=None,
        description="Update trusted status (e.g. after user confirmation prompt).",
    )
    is_active: bool | None = Field(
        default=None,
        description="Set False to soft-deactivate the device.",
    )
    timezone: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=20)
    last_active_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of the most recent activity from this device.",
    )
