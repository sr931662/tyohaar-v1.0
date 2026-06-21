"""
Users domain — internal / admin schemas.

These schemas are ORM-mapped and INCLUDE sensitive fields that must
never appear in public-facing API responses:
  - UserInternal       → failed_login_count, account_locked_until,
                         password_last_changed_at, last_password_reset_at,
                         deleted_at, is_deleted
  - UserProfileInternal → extra_metadata, emergency_contact_phone
  - UserDeviceInternal  → push_notification_token
  - UserAdminStats      → aggregate role distribution for admin dashboards

Usage:
  - Admin dashboards and internal tooling only.
  - MUST NOT be used as the response_model in public FastAPI routes.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field

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
    "UserInternal",
    "UserProfileInternal",
    "UserDeviceInternal",
    "UserAdminStats",
]


class UserInternal(IDSchema, TimestampSchema):
    """
    Full internal representation of a User account.

    SENSITIVE — includes security and soft-delete fields:
      failed_login_count, account_locked_until,
      password_last_changed_at, last_password_reset_at,
      deleted_at, is_deleted.

    Restricted to admin user-management and fraud-detection endpoints.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    phone: str
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

    # ── SENSITIVE security fields ──────────────────────────────────────────────
    failed_login_count: int = Field(
        ge=0,
        description=(
            "Number of consecutive failed login attempts. "
            "INTERNAL — never expose publicly."
        ),
    )
    account_locked_until: datetime | None = Field(
        default=None,
        description=(
            "UTC datetime until which the account is locked after too many "
            "failed attempts. INTERNAL — never expose publicly."
        ),
    )
    password_last_changed_at: datetime | None = Field(
        default=None,
        description=(
            "UTC datetime of the last password change. "
            "INTERNAL — never expose publicly."
        ),
    )
    last_password_reset_at: datetime | None = Field(
        default=None,
        description=(
            "UTC datetime of the last admin-initiated password reset. "
            "INTERNAL — never expose publicly."
        ),
    )
    # ── Soft-delete fields ─────────────────────────────────────────────────────
    deleted_at: datetime | None = Field(
        default=None,
        description=(
            "UTC datetime when the user account was soft-deleted. "
            "INTERNAL — never expose publicly."
        ),
    )
    is_deleted: bool = Field(
        default=False,
        description="True if the record has been soft-deleted. INTERNAL.",
    )
    # ──────────────────────────────────────────────────────────────────────────


class UserProfileInternal(IDSchema, TimestampSchema):
    """
    Full internal representation of a UserProfile.

    SENSITIVE — includes extra_metadata (JSONB) and emergency_contact_phone.
    Restricted to admin user-management endpoints.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID
    profile_photo_url: str | None = None
    cover_image_url: str | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    anniversary_date: date | None = None
    occupation: str | None = None
    bio: str | None = None
    religion: str | None = None
    preferred_language: Language
    timezone: str
    preferred_currency: Currency
    city: str | None = None
    state: str | None = None
    country: str | None = None
    pincode: str | None = None
    alternate_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = Field(
        default=None,
        description=(
            "Emergency contact's phone number. "
            "SEMI-SENSITIVE — available in admin view only."
        ),
    )
    emergency_contact_relation: str | None = None

    # ── SENSITIVE ──────────────────────────────────────────────────────────────
    extra_metadata: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Arbitrary JSONB metadata managed by the platform. "
            "INTERNAL — never expose publicly."
        ),
    )
    # ──────────────────────────────────────────────────────────────────────────


class UserDeviceInternal(IDSchema, TimestampSchema):
    """
    Full internal representation of a UserDevice.

    SENSITIVE — includes push_notification_token for push service use.
    Restricted to push notification services and device management endpoints.
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
    is_rooted: bool | None = None

    # ── SENSITIVE ──────────────────────────────────────────────────────────────
    push_notification_token: str | None = Field(
        default=None,
        description=(
            "FCM (Android) or APNs (iOS) push notification token. "
            "SENSITIVE — for push service use only; never expose publicly."
        ),
    )
    # ──────────────────────────────────────────────────────────────────────────


class UserAdminStats(BaseSchema):
    """
    Aggregate user statistics for admin dashboards.

    Provides role-level and status-level counts derived from the users table.
    Returned by `GET /admin/users/stats`.
    """

    model_config = ConfigDict(populate_by_name=True)

    total_users: int = Field(ge=0, description="Total number of user records.")
    active_users: int = Field(ge=0, description="Users with account_status=ACTIVE.")
    suspended_users: int = Field(ge=0, description="Users with account_status=SUSPENDED.")
    banned_users: int = Field(ge=0, description="Users with account_status=BANNED.")
    pending_verification: int = Field(
        ge=0,
        description="Users with account_status=PENDING_VERIFICATION.",
    )

    # Role distribution
    role_counts: dict[str, int] = Field(
        description=(
            "Per-role user count. Keys are UserRole values "
            "(e.g. 'customer', 'vendor', 'admin')."
        )
    )

    # Verification stats
    phone_verified_count: int = Field(ge=0)
    email_verified_count: int = Field(ge=0)
    mfa_enabled_count: int = Field(ge=0)

    # Registration trend (last 30 days)
    new_users_last_30_days: int = Field(
        ge=0,
        description="Users registered within the last 30 calendar days.",
    )
