"""
Users domain — common annotated types, nested helpers, and enum re-exports.

Import from here rather than directly from app.models.enums so that
user schema modules have a single, stable import surface.
"""

from __future__ import annotations

import re
from decimal import Decimal

from pydantic import Field

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
from app.schemas.base import BaseSchema, PhoneNumber

# ── Re-export enums for user consumers ────────────────────────────────────────

__all__ = [
    # Enums
    "UserRole",
    "UserType",
    "AccountStatus",
    "VerificationStatus",
    "LoginMethod",
    "Gender",
    "Language",
    "Currency",
    "AddressType",
    "DeviceType",
    "Platform",
    # Annotated types
    "PhoneNumber",
    # Nested schemas
    "DisplayNameSchema",
    "LocationSchema",
    "EmergencyContactSchema",
    # Helpers
    "normalize_phone",
    "PHONE_RE",
]

# ── Regex helpers ──────────────────────────────────────────────────────────────

PHONE_RE = re.compile(r"^\+[1-9]\d{9,14}$")


def normalize_phone(value: str) -> str:
    """
    Strip whitespace and validate E.164 format.

    Called by `@field_validator("phone", mode="before")` in Create/Update schemas.
    Raises ValueError with a developer-friendly message on invalid input.
    """
    stripped = value.strip()
    if not PHONE_RE.match(stripped):
        raise ValueError(
            f"Phone number must be in E.164 format (e.g. +919876543210), got: {stripped!r}"
        )
    return stripped


# ── Nested helper schemas ──────────────────────────────────────────────────────


class DisplayNameSchema(BaseSchema):
    """
    Resolved display name for a user.

    The service layer computes this from the priority chain:
        full_name → username → phone (last 4 digits masked)
    Exposed as a computed field in UserResponse.
    """

    display_name: str = Field(
        description=(
            "Best available display name: full_name, then username, "
            "then masked phone number."
        )
    )


class LocationSchema(BaseSchema):
    """
    Structured location sub-object for profile and address schemas.

    Used as a nested type for read responses; for write operations the
    fields are flattened directly onto the parent schema.
    """

    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=10)


class EmergencyContactSchema(BaseSchema):
    """
    Emergency contact details extracted from a UserProfile.

    The phone number is intentionally excluded from public display schemas
    and should be shown in full only in internal/admin views.
    """

    name: str | None = Field(
        default=None,
        max_length=200,
        description="Full name of the emergency contact.",
    )
    relation: str | None = Field(
        default=None,
        max_length=100,
        description="Relationship to the user (e.g. 'Spouse', 'Parent').",
    )
