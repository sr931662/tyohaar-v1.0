"""
PATCH request body schemas for the vendors domain.

All fields are Optional so clients can send partial updates.
None means "leave unchanged"; explicit null is not accepted unless
the field is explicitly nullable in the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import VendorType, PackagePricingType, ServiceStatus
from app.schemas.vendors.common import PriceTierSchema

__all__ = [
    "VendorUpdate",
    "VendorProfileUpdate",
    "VendorServiceUpdate",
    "VendorBankAccountUpdate",
    "VendorReviewUpdate",
]


class VendorUpdate(BaseSchema):
    """
    PATCH payload for a Vendor record.

    Only supply the fields you wish to change.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    business_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
        description="Updated public-facing trading name",
    )
    vendor_type: VendorType | None = Field(
        default=None,
        description="Updated primary service category",
    )
    legal_name: str | None = Field(
        default=None,
        max_length=300,
        description="Registered legal entity name as per government documents",
    )
    registration_number: str | None = Field(
        default=None,
        max_length=100,
    )
    gst_number: str | None = Field(
        default=None,
        max_length=20,
        description="15-character GST Identification Number (GSTIN)",
    )
    pan_number: str | None = Field(
        default=None,
        max_length=10,
        description="10-character Permanent Account Number",
    )
    service_radius_km: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        decimal_places=2,
    )
    years_of_experience: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    established_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )
    is_active: bool | None = Field(
        default=None,
        description="Soft-toggle the vendor's active flag",
    )


class VendorProfileUpdate(BaseSchema):
    """PATCH payload for a VendorProfile record."""

    model_config = ConfigDict(str_strip_whitespace=True)

    logo_url: str | None = Field(default=None, max_length=2048)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    tagline: str | None = Field(default=None, max_length=300)
    about: str | None = Field(default=None)
    specialties: list[str] | None = Field(default=None)
    working_hours: dict[str, Any] | None = Field(
        default=None,
        description='Daily working-hour slots e.g. {"mon": {"open": "09:00", "close": "18:00"}}',
    )
    holiday_calendar: list[str] | None = Field(
        default=None,
        description="ISO 8601 date strings for unavailable days",
    )
    operating_cities: list[str] | None = Field(default=None)
    operating_pincodes: list[str] | None = Field(default=None)
    website_url: str | None = Field(default=None, max_length=2048)
    social_links: dict[str, str] | None = Field(default=None)

    @field_validator("operating_pincodes", mode="before")
    @classmethod
    def validate_pincodes(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        for pincode in v:
            if not pincode.isdigit() or len(pincode) != 6:
                raise ValueError(f"Invalid Indian pincode: {pincode!r}")
        return v


class VendorServiceUpdate(BaseSchema):
    """PATCH payload for a VendorService record."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=300)
    description: str | None = Field(default=None)
    pricing_type: PackagePricingType | None = Field(default=None)
    base_price: MoneyAmount | None = Field(default=None)
    price_details: list[PriceTierSchema] | None = Field(
        default=None,
        description="Replacement tiered pricing steps",
    )
    min_order_amount: MoneyAmount | None = Field(default=None)
    max_capacity_persons: int | None = Field(default=None, ge=1)
    advance_booking_days: int | None = Field(default=None, ge=0, le=730)
    status: ServiceStatus | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class VendorBankAccountUpdate(BaseSchema):
    """
    PATCH payload for a VendorBankAccount record.

    Only operational flags are updatable after creation; to change
    account details the vendor must create a new account.
    """

    is_primary: bool | None = Field(
        default=None,
        description="Promote this account to the primary payout account",
    )
    is_verified: bool | None = Field(
        default=None,
        description="Admin-set verification flag after penny-drop validation",
    )
    verified_at: datetime | None = Field(
        default=None,
        description="Timestamp when the account was verified (UTC)",
    )


class VendorReviewUpdate(BaseSchema):
    """
    PATCH payload for a VendorReview.

    Vendors may add/update their response; admins may toggle publication.
    """

    is_published: bool | None = Field(
        default=None,
        description="Admin toggle to publish or suppress the review",
    )
    vendor_response: str | None = Field(
        default=None,
        max_length=5000,
        description="Vendor's public reply to this review",
    )
