"""
POST request body schemas for the vendors domain.

Each schema validates the payload for creating a new vendor-related
resource. They are NOT ORM-mapped (no from_attributes).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import VendorType, PackagePricingType
from app.schemas.vendors.common import PriceTierSchema

__all__ = [
    "VendorCreate",
    "VendorProfileCreate",
    "VendorServiceCreate",
    "VendorDocumentCreate",
    "VendorBankAccountCreate",
    "VendorReviewCreate",
]


class VendorCreate(BaseSchema):
    """
    Payload for registering a new vendor on the platform.

    One vendor record is allowed per user account (enforced at the DB
    level via a UNIQUE constraint on user_id).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: uuid.UUID = Field(description="FK to the owning user account")
    business_name: str = Field(
        min_length=2,
        max_length=200,
        description="Public-facing trading name of the vendor business",
    )
    vendor_type: VendorType = Field(description="Primary service category")
    legal_name: str | None = Field(
        default=None,
        max_length=300,
        description="Registered legal entity name as per government documents",
    )
    registration_number: str | None = Field(
        default=None,
        max_length=100,
        description="Company / LLP / shop-act registration number (optional)",
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
    years_of_experience: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Self-reported years of experience in the trade",
    )
    established_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Year the business was established",
    )
    service_radius_km: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        decimal_places=2,
        description="Maximum distance (km) the vendor is willing to travel",
    )

    @field_validator("business_name", mode="before")
    @classmethod
    def strip_business_name(cls, v: str) -> str:
        return v.strip()


class VendorProfileCreate(BaseSchema):
    """
    Payload for creating the rich profile page for a vendor.

    One profile per vendor — enforced via UNIQUE constraint on vendor_id.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    vendor_id: uuid.UUID = Field(description="FK to the parent vendor")
    logo_url: str | None = Field(default=None, max_length=2048)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    tagline: str | None = Field(default=None, max_length=300)
    about: str | None = Field(default=None, description="Free-text bio / about section")
    specialties: list[str] | None = Field(
        default=None,
        description="List of specialty tags (e.g. ['Mehendi', 'Bridal makeup'])",
    )
    working_hours: dict[str, Any] | None = Field(
        default=None,
        description='Daily working-hour slots, e.g. {"mon": {"open": "09:00", "close": "18:00"}}',
    )
    holiday_calendar: list[str] | None = Field(
        default=None,
        description="ISO 8601 date strings (YYYY-MM-DD) on which the vendor is unavailable",
    )
    operating_cities: list[str] | None = Field(
        default=None,
        description="List of city names where the vendor operates",
    )
    operating_pincodes: list[str] | None = Field(
        default=None,
        description="List of Indian pincodes the vendor serves",
    )
    website_url: str | None = Field(default=None, max_length=2048)
    social_links: dict[str, str] | None = Field(
        default=None,
        description='Platform → URL mapping, e.g. {"instagram": "https://instagram.com/..."}',
    )

    @field_validator("operating_pincodes", mode="before")
    @classmethod
    def validate_pincodes(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        for pincode in v:
            if not pincode.isdigit() or len(pincode) != 6:
                raise ValueError(f"Invalid Indian pincode: {pincode!r}")
        return v


class VendorServiceCreate(BaseSchema):
    """Payload for adding a new service offering under a vendor."""

    model_config = ConfigDict(str_strip_whitespace=True)

    vendor_id: uuid.UUID = Field(description="FK to the owning vendor")
    category_id: uuid.UUID = Field(description="FK to the VendorCategory")
    name: str = Field(min_length=2, max_length=300, description="Service display name")
    description: str | None = Field(default=None)
    pricing_type: PackagePricingType = Field(description="How the service is priced")
    base_price: MoneyAmount = Field(description="Base price / starting price in INR")
    price_details: list[PriceTierSchema] | None = Field(
        default=None,
        description="Tiered pricing steps — only relevant when pricing_type=TIERED",
    )
    min_order_amount: MoneyAmount | None = Field(
        default=None,
        description="Minimum order value required to book this service",
    )
    max_capacity_persons: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of guests this service can accommodate",
    )
    advance_booking_days: int | None = Field(
        default=None,
        ge=0,
        le=730,
        description="Minimum days in advance the service must be booked",
    )
    experience_years: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Years of specific experience for this service type",
    )

    @model_validator(mode="after")
    def validate_tiered_pricing(self) -> "VendorServiceCreate":
        if self.pricing_type == PackagePricingType.TIERED and not self.price_details:
            raise ValueError(
                "price_details is required when pricing_type is TIERED"
            )
        return self


class VendorDocumentCreate(BaseSchema):
    """Payload for uploading a KYC/compliance document for a vendor."""

    vendor_id: uuid.UUID = Field(description="FK to the owning vendor")
    document_type: str = Field(
        min_length=1,
        max_length=100,
        description='Type identifier, e.g. "gst_certificate", "pan_card", "aadhar"',
    )
    document_url: str = Field(
        max_length=2048,
        description="Signed URL or object-storage path of the uploaded document",
    )


class VendorBankAccountCreate(BaseSchema):
    """
    Payload for adding a bank account for vendor payouts.

    The account_number is stored encrypted at rest; only the last 4 digits
    are exposed in public responses.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    vendor_id: uuid.UUID = Field(description="FK to the owning vendor")
    account_holder_name: str = Field(
        min_length=2,
        max_length=200,
        description="Name as it appears on the bank account",
    )
    account_number: str = Field(
        min_length=6,
        max_length=50,
        description="Full bank account number (stored encrypted)",
    )
    ifsc_code: str = Field(
        min_length=11,
        max_length=11,
        description="11-character Indian Financial System Code",
    )
    bank_name: str = Field(min_length=2, max_length=200)
    branch_name: str | None = Field(default=None, max_length=200)
    is_primary: bool = Field(
        default=False,
        description="Whether this account should be the default payout account",
    )

    @field_validator("ifsc_code", mode="before")
    @classmethod
    def normalise_ifsc(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("account_number", mode="before")
    @classmethod
    def strip_account_number(cls, v: str) -> str:
        return v.strip().replace(" ", "")


class VendorReviewCreate(BaseSchema):
    """
    Payload for submitting a review for a completed booking.

    Reviews are only allowed from customers who have a verified booking
    with the vendor (is_verified enforced at the service layer).
    """

    vendor_id: uuid.UUID = Field(description="FK to the vendor being reviewed")
    booking_id: uuid.UUID = Field(
        description="FK to the Booking that qualifies this reviewer"
    )
    reviewer_id: uuid.UUID = Field(description="FK to the reviewing User")
    rating: int = Field(ge=1, le=5, description="Star rating from 1 (worst) to 5 (best)")
    title: str | None = Field(default=None, max_length=200, description="Optional review headline")
    body: str | None = Field(
        default=None,
        max_length=5000,
        description="Detailed review text",
    )
