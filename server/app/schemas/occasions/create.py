"""
POST request body schemas for the occasions domain.

Each schema validates the payload for creating a new occasion-related
resource. They are NOT ORM-mapped (no from_attributes).
"""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import (
    OccasionCategory,
    CelebrationStatus,
    Currency,
    RSVPStatus,
)

__all__ = [
    "CelebrationCreate",
    "CelebrationGuestCreate",
    "CelebrationChecklistCreate",
    "OccasionCreate",
    "GuestRSVPSubmit",
]


class CelebrationCreate(BaseSchema):
    """
    Payload for planning a new celebration tied to an occasion.

    Either venue_address (free text) or venue_address_id (saved address)
    can be provided; both may be set for display convenience.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: uuid.UUID = Field(description="FK to the planning customer")
    occasion_id: uuid.UUID = Field(description="FK to the Occasion type")
    theme_id: uuid.UUID | None = Field(
        default=None, description="Optional FK to an OccasionTheme"
    )
    mood_id: uuid.UUID | None = Field(
        default=None, description="Optional FK to an OccasionMood"
    )
    title: str = Field(
        min_length=1,
        max_length=300,
        description="Short descriptive title for this celebration",
    )
    description: str | None = Field(
        default=None, description="Longer free-text description or special notes"
    )
    celebration_date: date = Field(description="Calendar date of the celebration")
    start_time: time | None = Field(
        default=None, description="Start time on the celebration date"
    )
    end_time: time | None = Field(
        default=None, description="End time on the celebration date"
    )
    guest_count: int = Field(
        default=0, ge=0, description="Expected number of guests"
    )
    # Venue
    venue_name: str | None = Field(default=None, max_length=300)
    venue_address: str | None = Field(
        default=None, description="Free-text venue address"
    )
    venue_address_id: uuid.UUID | None = Field(
        default=None, description="FK to a saved UserAddress"
    )
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
    # Financials
    currency: Currency = Field(default=Currency.INR)
    estimated_budget: MoneyAmount | None = Field(
        default=None, description="Estimated total spend for the celebration"
    )
    special_instructions: str | None = Field(
        default=None, description="Any special instructions for vendors / coordinators"
    )

    @model_validator(mode="after")
    def validate_time_range(self) -> "CelebrationCreate":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValueError("end_time must be after start_time")
        return self

    @model_validator(mode="after")
    def validate_coordinates(self) -> "CelebrationCreate":
        lat_provided = self.latitude is not None
        lng_provided = self.longitude is not None
        if lat_provided != lng_provided:
            raise ValueError("latitude and longitude must both be provided together")
        return self

    @field_validator("celebration_date", mode="before")
    @classmethod
    def validate_future_date(cls, v: date) -> date:
        if isinstance(v, str):
            from datetime import date as dt_date
            v = dt_date.fromisoformat(v)
        return v


class CelebrationGuestCreate(BaseSchema):
    """
    Payload for adding a guest to a celebration's guest list.

    Phone and email are optional; RSVP status defaults to PENDING.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200, description="Guest's full name")
    phone: str | None = Field(
        default=None,
        max_length=15,
        description="Guest's phone number (with country code)",
    )
    email: str | None = Field(
        default=None,
        max_length=320,
        description="Guest's email address",
    )
    rsvp_status: RSVPStatus = Field(
        default=RSVPStatus.PENDING,
        description="Guest's RSVP state",
    )
    group_tag: str | None = Field(
        default=None,
        max_length=100,
        description="Informal grouping label (e.g. 'Family', 'Colleagues', 'School Friends').",
    )
    notes: str | None = Field(
        default=None,
        description="Free-text notes about this guest (dietary restrictions, etc.)",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip().lower()
        return v


class CelebrationChecklistCreate(BaseSchema):
    """Payload for adding a to-do item to a celebration's checklist."""

    model_config = ConfigDict(str_strip_whitespace=True)

    celebration_id: uuid.UUID = Field(description="FK to the parent Celebration")
    title: str = Field(min_length=1, max_length=300, description="Checklist item title")
    description: str | None = Field(default=None)
    is_completed: bool = Field(default=False)
    due_date: date | None = Field(
        default=None,
        description="Optional deadline for this checklist item",
    )
    display_order: int = Field(
        default=0,
        ge=0,
        description="Sort position within the checklist (ascending)",
    )


class OccasionCreate(BaseSchema):
    """
    Admin-only payload for creating a new Occasion type.

    End-users cannot create occasions; this is a platform-managed catalogue.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200, description="Display name of the occasion")
    slug: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-safe slug (lowercase, hyphens only)",
    )
    category: OccasionCategory = Field(description="Broad category bucket for this occasion")
    description: str | None = Field(default=None)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    icon_url: str | None = Field(default=None, max_length=2048)
    display_order: int = Field(
        default=0,
        ge=0,
        description="Sort position in catalogue listings",
    )
    is_featured: bool = Field(
        default=False,
        description="Whether this occasion is highlighted on the home screen",
    )


class GuestRSVPSubmit(BaseSchema):
    """
    Payload a guest submits on the public (no-auth) RSVP page.

    Only ATTENDING/MAYBE/DECLINED are valid guest-submitted responses —
    PENDING/NO_RESPONSE are system states, never chosen by the guest.
    """

    rsvp_status: RSVPStatus = Field(description="Guest's response: attending, maybe, or declined.")
    notes: str | None = Field(default=None, max_length=1000, description="Optional note from the guest (dietary needs, etc.)")

    @field_validator("rsvp_status")
    @classmethod
    def validate_guest_choosable_status(cls, v: RSVPStatus) -> RSVPStatus:
        if v not in (RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.DECLINED):
            raise ValueError("rsvp_status must be one of: attending, maybe, declined")
        return v
