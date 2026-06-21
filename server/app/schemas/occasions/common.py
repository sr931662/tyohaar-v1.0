"""
Shared nested types and enum re-exports for the occasions domain.

Import from this module when you need celebration sub-objects (time slots,
venue details) or occasion-related enum values in other occasion schema files.
"""

from __future__ import annotations

import uuid
from datetime import time
from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseSchema
from app.models.enums import (
    OccasionCategory,
    CelebrationStatus,
    Currency,
    RSVPStatus,
)

__all__ = [
    # nested types
    "TimeSlotSchema",
    "VenueSchema",
    # enums
    "OccasionCategory",
    "CelebrationStatus",
    "Currency",
    "RSVPStatus",
]


class TimeSlotSchema(BaseSchema):
    """
    A start-to-end time range for a celebration event.

    Both fields use Python's `datetime.time` type (HH:MM:SS).
    """

    start_time: time = Field(description="Event start time")
    end_time: time = Field(description="Event end time")

    def model_post_init(self, __context: object) -> None:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")


class VenueSchema(BaseSchema):
    """
    Venue details for a celebration.

    Either a free-text address or a reference to a saved UserAddress
    (venue_address_id) can be provided, or both for display convenience.
    Coordinates (latitude/longitude) are optional for geo-features.
    """

    venue_name: str | None = Field(
        default=None,
        max_length=300,
        description="Display name of the venue (e.g. 'The Grand Hyatt, Mumbai')",
    )
    venue_address: str | None = Field(
        default=None,
        description="Free-text postal address of the venue",
    )
    venue_address_id: uuid.UUID | None = Field(
        default=None,
        description="FK to a saved UserAddress record",
    )
    latitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-90"),
        le=Decimal("90"),
        decimal_places=7,
        description="WGS-84 latitude",
    )
    longitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-180"),
        le=Decimal("180"),
        decimal_places=7,
        description="WGS-84 longitude",
    )
