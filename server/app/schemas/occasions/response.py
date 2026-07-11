"""
GET response schemas for the occasions domain.

All schemas are ORM-mapped (from_attributes=True) and MUST NOT expose
any sensitive fields. Specifically excluded from Celebration responses:
- internal_notes / extra_metadata  (NotesMixin / MetadataMixin)
- deleted_at / is_deleted          (SoftDeleteMixin)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import ConfigDict, Field, computed_field

from app.schemas.base import BaseSchema
from app.models.enums import (
    CelebrationStatus,
    Currency,
    RSVPStatus,
)

__all__ = [
    "OccasionResponse",
    "OccasionThemeResponse",
    "OccasionMoodResponse",
    "OccasionTagResponse",
    "CelebrationResponse",
    "CelebrationGuestResponse",
    "CelebrationChecklistResponse",
    "GuestRSVPPublicResponse",
]

_ORM = ConfigDict(from_attributes=True, populate_by_name=True)


class OccasionResponse(BaseSchema):
    """
    Public occasion catalogue entry.

    Represents a single type of occasion (e.g. Wedding, Diwali) that
    customers can use when planning a celebration.
    """

    model_config = _ORM

    id: uuid.UUID
    name: str
    slug: str
    category_id: uuid.UUID | None = None
    description: str | None = None
    icon_url: str | None = None
    banner_url: str | None = None
    thumbnail_url: str | None = None
    is_active: bool
    display_order: int
    is_featured: bool
    created_at: datetime


class OccasionThemeResponse(BaseSchema):
    """
    A visual theme that customers can associate with their celebration.

    Themes carry a colour palette and a preview image for the theme picker UI.
    """

    model_config = _ORM

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    cover_image_url: str | None = None
    thumbnail_url: str | None = None
    colors: dict[str, str] | None = Field(
        default=None,
        description="Color palette: {primary, secondary, accent, background} hex codes.",
    )
    sort_order: int
    is_active: bool
    is_featured: bool


class OccasionMoodResponse(BaseSchema):
    """
    A mood/vibe tag for a celebration (e.g. 'Romantic', 'Fun & Festive').
    """

    model_config = _ORM

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    emoji: str | None = Field(default=None, description="Single emoji representing the mood")
    is_active: bool


class OccasionTagResponse(BaseSchema):
    """A keyword tag that can be attached to occasion content."""

    model_config = _ORM

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool


class CelebrationResponse(BaseSchema):
    """
    A customer's individual celebration plan.

    Safe for serving to the owning customer and their invited collaborators.
    Does NOT include internal_notes, extra_metadata, or deleted_at.
    """

    model_config = _ORM

    id: uuid.UUID
    customer_id: uuid.UUID
    occasion_id: uuid.UUID
    theme_id: uuid.UUID | None = None
    mood_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    celebration_date: date
    start_time: time | None = None
    end_time: time | None = None
    guest_count: int
    # Venue
    venue_name: str | None = None
    venue_address: str | None = None
    venue_address_id: uuid.UUID | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    # Status & progress
    status: CelebrationStatus
    completion_percentage: int = Field(
        ge=0,
        le=100,
        description="Planning progress (0–100 %)",
    )
    # Financials
    currency: Currency
    estimated_budget: Decimal | None = None
    final_budget: Decimal | None = None
    special_instructions: str | None = None
    # Timestamps
    created_at: datetime
    updated_at: datetime
    # Denormalized display data — the backend does not nest occasion/theme
    # objects, so the customer app cannot resolve names/colors/images from
    # occasion_id/theme_id alone. Populated by the service layer at read
    # time (batch-fetched, not a relationship load).
    occasion_name: str | None = None
    occasion_hero_image_url: str | None = None
    theme_colors: dict[str, str] | None = None
    theme_cover_image_url: str | None = None


class CelebrationGuestResponse(BaseSchema):
    """
    A single guest on a celebration's guest list.

    Phone and email are optional in the response for privacy — the API
    layer should restrict access to the celebration owner only.
    """

    model_config = _ORM

    id: uuid.UUID
    celebration_id: uuid.UUID
    name: str
    # Privacy-sensitive: only return to the celebration owner
    phone: str | None = None
    email: str | None = None
    rsvp_status: RSVPStatus
    group_tag: str | None = None
    notes: str | None = None
    rsvp_token: str | None = Field(
        default=None,
        description="Opaque token for the public RSVP link — only meaningful to the celebration owner sharing an invite.",
    )
    invitation_opened_at: datetime | None = None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_status(self) -> str:
        """
        coming/maybe/declined mirror rsvp_status once the guest has responded.
        Before any response: 'pending' if the invite link was never opened,
        'ignored' if it was opened but the guest never submitted a response.
        Re-opening and responding later (up to the day before the event) just
        updates rsvp_status normally — this is purely a display computation,
        not a stored terminal state.
        """
        if self.rsvp_status != RSVPStatus.PENDING:
            return self.rsvp_status.value
        return "ignored" if self.invitation_opened_at is not None else "pending"


class GuestRSVPPublicResponse(BaseSchema):
    """
    Public (no-auth) view shown to a guest on their personal RSVP link.

    Deliberately minimal — no other guests, no host phone/email, no
    celebration owner identity beyond the event details needed to decide
    whether to attend.
    """

    guest_name: str
    rsvp_status: RSVPStatus
    can_still_respond: bool = Field(
        description="False once it's past the response cutoff (the day before the event)."
    )
    celebration_title: str
    celebration_date: date
    venue_name: str | None = None
    venue_address: str | None = None


class CelebrationChecklistResponse(BaseSchema):
    """A single checklist item within a celebration plan."""

    model_config = _ORM

    id: uuid.UUID
    celebration_id: uuid.UUID
    title: str
    description: str | None = None
    is_completed: bool
    due_date: date | None = None
    completed_at: datetime | None = None
    display_order: int
    created_at: datetime
