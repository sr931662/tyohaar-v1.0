"""
GET response schemas for the vendors domain.

All schemas here are ORM-mapped (from_attributes=True) and MUST NOT
expose any sensitive fields. See security rules in the module docstring.

NEVER expose:
- internal_notes / extra_metadata (NotesMixin / MetadataMixin)
- deleted_at / is_deleted (SoftDeleteMixin)
- legal_name, gst_number, pan_number (tax compliance — admin only)
- priority_score, assigned_account_manager_id (internal ops — admin only)
- gateway_signature, push_notification_token, device_fingerprint
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, computed_field, field_serializer

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    VendorType,
    VendorStatus,
    VendorVerificationStatus,
    ServiceStatus,
    PackagePricingType,
    VerificationStatus,
)

__all__ = [
    "VendorResponse",
    "VendorSelfResponse",
    "VendorProfileResponse",
    "VendorServiceResponse",
    "VendorCategoryResponse",
    "VendorDocumentResponse",
    "VendorBankAccountResponse",
    "VendorReviewResponse",
]

_ORM = ConfigDict(from_attributes=True, populate_by_name=True)


class VendorResponse(BaseSchema):
    """
    Public-facing vendor record.

    Suitable for listing and detail pages. Does NOT include compliance
    fields (legal_name, gst_number, pan_number), internal ops fields
    (priority_score, assigned_account_manager_id), or audit internals.
    """

    model_config = _ORM

    id: uuid.UUID
    user_id: uuid.UUID
    business_name: str
    vendor_type: VendorType
    registration_number: str | None = None
    verification_status: VendorVerificationStatus
    status: VendorStatus
    is_active: bool
    service_radius_km: Decimal | None = None
    years_of_experience: int | None = None
    established_year: int | None = None
    average_rating: Decimal | None = Field(
        default=None,
        description="Aggregate rating (0.00 – 5.00)",
    )
    review_count: int = 0
    completion_count: int = 0
    cancellation_count: int = 0
    acceptance_rate_pct: Decimal | None = None
    avg_response_time_minutes: int | None = None
    created_at: datetime
    updated_at: datetime


class VendorSelfResponse(VendorResponse):
    """
    Vendor's own view of their record — returned only by `GET /vendors/me`.

    Unlike VendorResponse (public/listing-safe), this includes the vendor's
    own compliance fields so they can see and edit what they submitted.
    Never use this for any endpoint another user's request can reach.
    """

    legal_name: str | None = None
    gst_number: str | None = None
    pan_number: str | None = None


class VendorProfileResponse(BaseSchema):
    """
    Rich profile data for a vendor (bio, images, operating areas).

    Safe for public display — no compliance or ops fields.
    """

    model_config = _ORM

    id: uuid.UUID
    vendor_id: uuid.UUID
    logo_url: str | None = None
    cover_image_url: str | None = None
    tagline: str | None = None
    about: str | None = None
    specialties: list[str] | None = None
    working_hours: dict[str, Any] | None = Field(
        default=None,
        description='Daily schedule, e.g. {"mon": {"open": "09:00", "close": "18:00"}}',
    )
    holiday_calendar: list[str] | None = None
    operating_cities: list[str] | None = None
    operating_pincodes: list[str] | None = None
    website_url: str | None = None
    social_links: dict[str, str] | None = None


class VendorServiceResponse(BaseSchema):
    """A single service offering listed under a vendor."""

    model_config = _ORM

    id: uuid.UUID
    vendor_id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: str | None = None
    pricing_type: PackagePricingType
    base_price: Decimal
    price_details: list[dict[str, Any]] | None = None
    min_order_amount: Decimal | None = None
    max_capacity_persons: int | None = None
    advance_booking_days: int | None = None
    experience_years: int | None = None
    status: ServiceStatus
    is_active: bool


class VendorCategoryResponse(BaseSchema):
    """A vendor service category (e.g. Photography, Catering)."""

    model_config = _ORM

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    icon_url: str | None = None
    is_active: bool
    display_order: int


class VendorDocumentResponse(BaseSchema):
    """
    KYC document record as shown on the vendor's own dashboard.

    The full document_url is returned here because this response is only
    served to the owning vendor and admins (enforced at the API layer).
    """

    model_config = _ORM

    id: uuid.UUID
    vendor_id: uuid.UUID
    document_type: str
    document_url: str
    verification_status: VerificationStatus
    verified_at: datetime | None = None
    rejection_reason: str | None = None
    is_active: bool


class VendorBankAccountResponse(BaseSchema):
    """
    Bank account record with the full account number masked.

    Only the last 4 digits of the account number are exposed.
    The raw account_number ORM field is consumed by the computed_field
    and is excluded from serialisation.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: uuid.UUID
    vendor_id: uuid.UUID
    account_holder_name: str
    # Raw field — read from ORM, used by the computed_field below.
    # Excluded from the serialised response via field_serializer.
    account_number: str = Field(exclude=True)
    ifsc_code: str
    bank_name: str
    branch_name: str | None = None
    is_primary: bool
    is_verified: bool
    verified_at: datetime | None = None

    @computed_field(description="Last 4 digits of the bank account number, masked")
    @property
    def account_number_masked(self) -> str:
        """Returns the account number as e.g. '****1234'."""
        raw = self.account_number or ""
        visible = raw[-4:] if len(raw) >= 4 else raw
        return f"****{visible}"


class VendorReviewResponse(BaseSchema):
    """
    A published vendor review visible to the public.

    Includes the vendor's response if one has been posted.
    """

    model_config = _ORM

    id: uuid.UUID
    vendor_id: uuid.UUID
    booking_id: uuid.UUID
    reviewer_id: uuid.UUID
    rating: int
    title: str | None = None
    body: str | None = None
    is_verified: bool
    is_published: bool
    vendor_response: str | None = None
    vendor_responded_at: datetime | None = None
    created_at: datetime
