"""
Shared nested types and enum re-exports for the vendors domain.

Import from this module whenever you need vendor-related sub-objects
(e.g. working-hours slots, tiered pricing) or enum values in other
vendor schema files.
"""

from __future__ import annotations

import uuid
from datetime import time
from decimal import Decimal
from typing import Annotated

from pydantic import Field

from app.schemas.base import BaseSchema
from app.models.enums import (
    VendorType,
    VendorStatus,
    VendorVerificationStatus,
    ServiceStatus,
    PackagePricingType,
    VerificationStatus,
    AvailabilityStatus,
    SettlementStatus,
)

# ── Re-exports so callers can do `from app.schemas.vendors.common import VendorType`
__all__ = [
    # nested types
    "TimeSlot",
    "WorkingHoursSchema",
    "PriceTierSchema",
    "SocialLinksSchema",
    # enums
    "VendorType",
    "VendorStatus",
    "VendorVerificationStatus",
    "ServiceStatus",
    "PackagePricingType",
    "VerificationStatus",
    "AvailabilityStatus",
    "SettlementStatus",
]


class TimeSlot(BaseSchema):
    """Opening and closing time for a single day of the week."""

    open: time = Field(description="Opening time (HH:MM)")
    close: time = Field(description="Closing time (HH:MM)")


# A mapping of lower-case day names to their TimeSlot.
# e.g. {"mon": {"open": "09:00", "close": "18:00"}}
WorkingHoursSchema = dict[str, TimeSlot]


class PriceTierSchema(BaseSchema):
    """
    A single price tier in a tiered-pricing service.

    Represents the price that applies when guest count falls within
    the [min_guests, max_guests] range (inclusive).
    """

    min_guests: int = Field(ge=1, description="Minimum guest count for this tier")
    max_guests: int | None = Field(
        default=None,
        description="Maximum guest count for this tier (null = unlimited)",
    )
    price: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=2,
        description="Price in INR (or vendor's operating currency) for this tier",
    )

    def model_post_init(self, __context: object) -> None:
        if (
            self.max_guests is not None
            and self.max_guests < self.min_guests
        ):
            raise ValueError("max_guests must be >= min_guests")


class SocialLinksSchema(BaseSchema):
    """
    Validated social-media link set for a vendor profile.

    All fields are optional; only the links the vendor provides are stored.
    """

    instagram: str | None = Field(default=None, max_length=2048)
    facebook: str | None = Field(default=None, max_length=2048)
    youtube: str | None = Field(default=None, max_length=2048)
    twitter: str | None = Field(default=None, max_length=2048)
    linkedin: str | None = Field(default=None, max_length=2048)
    website: str | None = Field(default=None, max_length=2048)
