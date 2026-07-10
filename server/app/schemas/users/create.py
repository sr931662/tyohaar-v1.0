"""
Users domain — POST request body schemas (Create).

These schemas validate inbound data for creating new user-domain entities.
They are NOT ORM-mapped; `from_attributes` is intentionally absent.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator, model_validator

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
from app.schemas.base import BaseSchema, Latitude, Longitude, PhoneNumber
from app.schemas.users.common import normalize_phone

__all__ = [
    "UserCreate",
    "UserProfileCreate",
    "UserAddressCreate",
    "UserDeviceCreate",
]


class UserCreate(BaseSchema):
    """
    Request body for `POST /users` (admin) or consumed internally during
    OTP-based registration flows.

    `phone` is the only required field; all other identifiers are optional
    because users may onboard incrementally.
    """

    model_config = ConfigDict(populate_by_name=True)

    phone: PhoneNumber = Field(
        description="Primary identifier in E.164 format (e.g. +919876543210)."
    )
    email: str | None = Field(
        default=None,
        max_length=320,
        description="Optional email address (RFC-5322).",
    )
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        description=(
            "Optional unique handle. "
            "Alphanumeric, underscores, hyphens, and dots only."
        ),
    )
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    role: UserRole = Field(
        default=UserRole.CUSTOMER,
        description="Authorization role. Defaults to CUSTOMER for self-registration.",
    )
    user_type: UserType = Field(
        default=UserType.INDIVIDUAL,
        description="INDIVIDUAL for personal accounts, BUSINESS for vendor accounts.",
    )

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)

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


class UserProfileCreate(BaseSchema):
    """
    Request body for `POST /users/{user_id}/profile`.

    Creates the one-to-one UserProfile record for a user. The user must
    already exist. `extra_metadata` is excluded — it is set only by the
    service layer.
    """

    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID = Field(description="UUID of the owning user.")

    # Media
    profile_photo_url: str | None = Field(default=None, max_length=2048)
    cover_image_url: str | None = Field(default=None, max_length=2048)

    # Personal details
    gender: Gender | None = None
    date_of_birth: date | None = Field(
        default=None,
        description="User's date of birth (YYYY-MM-DD). Used for age verification.",
    )
    anniversary_date: date | None = None
    occupation: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(
        default=None,
        description="Short free-text bio shown on the user's public profile.",
    )
    religion: str | None = Field(default=None, max_length=100)

    # Localisation preferences
    preferred_language: Language = Field(
        default=Language.ENGLISH,
        description="BCP-47 language tag for the user's preferred app language.",
    )
    timezone: str = Field(
        default="Asia/Kolkata",
        max_length=64,
        description="IANA timezone string (e.g. 'Asia/Kolkata', 'America/New_York').",
    )
    preferred_currency: Currency = Field(
        default=Currency.INR,
        description="ISO 4217 currency code for pricing display.",
    )

    # Location (profile-level, not delivery address)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default="India", max_length=100)
    pincode: str | None = Field(default=None, max_length=10)

    # Contact extras
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
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age > 120:
            raise ValueError("date_of_birth appears unreasonably far in the past.")
        return v


class UserAddressCreate(BaseSchema):
    """
    Request body for `POST /users/{user_id}/addresses`.

    Creates a new delivery/billing address for a user.
    Latitude/longitude are optional and expressed as Decimal for precision.
    """

    model_config = ConfigDict(populate_by_name=True)

    address_type: AddressType = Field(
        default=AddressType.HOME,
        description="Categorises the address (HOME, WORK, EVENT_VENUE, etc.).",
    )
    label: str | None = Field(
        default=None,
        max_length=100,
        description="Friendly label, e.g. 'Mom's house' or 'Office'.",
    )

    # Recipient
    recipient_name: str | None = Field(default=None, max_length=200)
    recipient_phone: str | None = Field(default=None, max_length=15)
    alternate_phone: str | None = Field(default=None, max_length=15)

    # Address lines
    address_line_1: str = Field(
        min_length=5,
        max_length=300,
        description="First line of the street address (required).",
    )
    address_line_2: str | None = Field(default=None, max_length=300)
    landmark: str | None = Field(default=None, max_length=200)
    locality: str | None = Field(default=None, max_length=200)

    # Geo hierarchy
    city: str = Field(min_length=1, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    country: str = Field(default="India", max_length=100)
    postal_code: str = Field(
        min_length=4,
        max_length=10,
        description="Postal / ZIP code.",
    )

    # Coordinates
    latitude: Latitude = None
    longitude: Longitude = None

    # Delivery notes
    delivery_instructions: str | None = Field(
        default=None,
        description="Special delivery instructions for the courier.",
    )
    is_default: bool = Field(
        default=False,
        description="Set True to make this the default address for the user.",
    )

    @field_validator("recipient_phone", "alternate_phone", mode="before")
    @classmethod
    def validate_optional_phone(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        return normalize_phone(v)

    @model_validator(mode="after")
    def validate_coordinates_paired(self) -> "UserAddressCreate":
        """Latitude and longitude must be supplied together or not at all."""
        has_lat = self.latitude is not None
        has_lng = self.longitude is not None
        if has_lat != has_lng:
            raise ValueError(
                "latitude and longitude must both be provided or both omitted."
            )
        return self


class UserDeviceCreate(BaseSchema):
    """
    Request body for `POST /users/{user_id}/devices`.

    Registers a new device for push notifications and session tracking.
    `push_notification_token` is accepted here (service-layer write path)
    but is never returned in public read responses.
    """

    model_config = ConfigDict(populate_by_name=True)

    device_id: str = Field(
        min_length=8,
        max_length=256,
        description="Stable unique identifier generated by the client SDK.",
    )
    device_type: DeviceType = Field(description="Physical form factor.")
    platform: Platform = Field(description="OS platform.")

    # Hardware / software metadata
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    os: str | None = Field(default=None, max_length=50)
    os_version: str | None = Field(default=None, max_length=50)
    app_version: str | None = Field(default=None, max_length=50)

    # Push token (service layer only — NEVER returned in responses)
    push_notification_token: str | None = Field(
        default=None,
        description=(
            "FCM (Android) or APNs (iOS) push notification token. "
            "Stored securely; never returned in read responses."
        ),
    )

    # Locale
    timezone: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=20)

    # Trust
    is_trusted: bool = Field(
        default=False,
        description="Mark as trusted only after explicit user confirmation.",
    )
