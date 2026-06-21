"""
PATCH request body schemas for the occasions domain.

All fields are Optional. None means "leave this field unchanged".
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import CelebrationStatus, Currency, RSVPStatus

__all__ = [
    "CelebrationUpdate",
    "CelebrationGuestUpdate",
    "CelebrationChecklistUpdate",
]


class CelebrationUpdate(BaseSchema):
    """
    PATCH payload for a Celebration record.

    Supply only the fields you wish to change.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    occasion_id: uuid.UUID | None = Field(
        default=None, description="Change the occasion type"
    )
    theme_id: uuid.UUID | None = Field(
        default=None, description="Change or set the theme"
    )
    mood_id: uuid.UUID | None = Field(
        default=None, description="Change or set the mood"
    )
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None)
    celebration_date: date | None = Field(
        default=None, description="Reschedule the celebration date"
    )
    start_time: time | None = Field(default=None)
    end_time: time | None = Field(default=None)
    guest_count: int | None = Field(default=None, ge=0)
    # Venue
    venue_name: str | None = Field(default=None, max_length=300)
    venue_address: str | None = Field(default=None)
    venue_address_id: uuid.UUID | None = Field(default=None)
    latitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-90"),
        le=Decimal("90"),
        decimal_places=7,
    )
    longitude: Decimal | None = Field(
        default=None,
        ge=Decimal("-180"),
        le=Decimal("180"),
        decimal_places=7,
    )
    # Status
    status: CelebrationStatus | None = Field(
        default=None, description="Advance the celebration lifecycle status"
    )
    # Financials
    estimated_budget: MoneyAmount | None = Field(default=None)
    special_instructions: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_time_range(self) -> "CelebrationUpdate":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValueError("end_time must be after start_time")
        return self

    @model_validator(mode="after")
    def validate_coordinates(self) -> "CelebrationUpdate":
        lat_provided = self.latitude is not None
        lng_provided = self.longitude is not None
        if lat_provided != lng_provided:
            raise ValueError("latitude and longitude must both be provided together")
        return self


class CelebrationGuestUpdate(BaseSchema):
    """
    PATCH payload for a CelebrationGuest.

    Customers update the RSVP state and guest notes after initial creation.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    rsvp_status: RSVPStatus | None = Field(
        default=None, description="Updated RSVP state for this guest"
    )
    notes: str | None = Field(
        default=None, description="Updated free-text notes about this guest"
    )


class CelebrationChecklistUpdate(BaseSchema):
    """PATCH payload for a CelebrationChecklist item."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None)
    is_completed: bool | None = Field(
        default=None,
        description="Mark the item as completed or uncompleted",
    )
    due_date: date | None = Field(default=None)
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the item was completed (UTC); set alongside is_completed=True",
    )
    display_order: int | None = Field(default=None, ge=0)
