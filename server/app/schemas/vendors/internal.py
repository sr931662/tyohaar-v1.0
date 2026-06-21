"""
Admin / internal schemas for the vendors domain.

These schemas MAY include sensitive fields that must never appear in
public API responses. They are ONLY served to admin endpoints guarded
by admin-role JWT verification.

Fields included here that are excluded from public schemas:
- legal_name, gst_number, pan_number  (tax compliance)
- internal_notes, extra_metadata      (NotesMixin / MetadataMixin)
- priority_score                      (internal ops ranking)
- assigned_account_manager_id         (internal ops)
- deleted_at                          (soft-delete audit)
- account_number (unmasked)           (full bank account number)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema
from app.models.enums import (
    VendorType,
    VendorStatus,
    VendorVerificationStatus,
)

__all__ = [
    "VendorInternal",
    "VendorBankAccountInternal",
    "VendorAdminStats",
]

_ADMIN_ORM = ConfigDict(from_attributes=True, populate_by_name=True)


class VendorInternal(BaseSchema):
    """
    Full vendor record for admin dashboards and internal tooling.

    Includes all sensitive fields excluded from the public VendorResponse.
    This schema MUST NOT be used in any endpoint accessible without
    admin-role authentication.
    """

    model_config = _ADMIN_ORM

    # Core identity
    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str
    vendor_type: VendorType
    registration_number: str | None = None

    # Admin-only compliance fields
    legal_name: str | None = Field(
        default=None,
        description="Legal / registered entity name — ADMIN ONLY",
    )
    gst_number: str | None = Field(
        default=None,
        description="GST Identification Number — ADMIN ONLY",
    )
    pan_number: str | None = Field(
        default=None,
        description="Permanent Account Number — ADMIN ONLY",
    )

    # Status
    verification_status: VendorVerificationStatus
    status: VendorStatus
    is_active: bool

    # Operational
    service_radius_km: Decimal | None = None
    years_of_experience: int | None = None
    established_year: int | None = None
    average_rating: Decimal | None = None
    review_count: int = 0
    completion_count: int = 0
    cancellation_count: int = 0
    acceptance_rate_pct: Decimal | None = None
    avg_response_time_minutes: int | None = None

    # Internal ops — ADMIN ONLY
    assigned_account_manager_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the admin account manager assigned to this vendor",
    )
    priority_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Internal ranking score used for search and promotions (0–100)",
    )

    # Audit fields
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    # Soft-delete — ADMIN ONLY
    deleted_at: datetime | None = Field(
        default=None,
        description="Timestamp of soft-deletion; null if the record is live",
    )

    # NotesMixin / MetadataMixin — ADMIN ONLY
    internal_notes: str | None = Field(
        default=None,
        description="Free-text notes for internal team use",
    )
    extra_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary JSON metadata for internal tooling",
    )


class VendorBankAccountInternal(BaseSchema):
    """
    Bank account record with the UNMASKED account number.

    Use only in admin endpoints where the caller has explicit
    'VIEW_SENSITIVE' permission logged to AuditLog.
    """

    model_config = _ADMIN_ORM

    id: uuid.UUID
    vendor_id: uuid.UUID
    account_holder_name: str
    # Full unmasked account number — ADMIN ONLY
    account_number: str = Field(description="Full bank account number — ADMIN ONLY")
    ifsc_code: str
    bank_name: str
    branch_name: str | None = None
    is_primary: bool
    is_verified: bool
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class VendorAdminStats(BaseSchema):
    """
    Lightweight performance statistics for a vendor, used in admin dashboards.

    Aggregates operational metrics and the internal priority score.
    """

    model_config = _ADMIN_ORM

    vendor_id: uuid.UUID
    completion_count: int = Field(
        description="Total number of bookings completed by this vendor"
    )
    cancellation_count: int = Field(
        description="Total number of bookings cancelled by or on behalf of this vendor"
    )
    acceptance_rate_pct: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
        decimal_places=2,
        description="Percentage of booking requests accepted (0–100)",
    )
    avg_response_time_minutes: int | None = Field(
        default=None,
        description="Average time (minutes) taken to respond to booking requests",
    )
    priority_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Internal ranking score (0–100) — ADMIN ONLY",
    )
