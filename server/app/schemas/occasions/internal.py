"""
Admin / internal schemas for the occasions domain.

These schemas MAY include sensitive fields that must never appear in
public API responses. Only serve from admin endpoints protected by
admin-role JWT verification.

Fields included here that are excluded from public schemas:
- internal_notes  (NotesMixin)
- extra_metadata  (MetadataMixin)
- deleted_at      (SoftDeleteMixin)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema
from app.models.enums import CelebrationStatus, Currency

__all__ = [
    "CelebrationInternal",
    "CelebrationSummary",
]

_ADMIN_ORM = ConfigDict(from_attributes=True, populate_by_name=True)


class CelebrationInternal(BaseSchema):
    """
    Full celebration record for admin dashboards and internal tooling.

    Includes all fields excluded from the public CelebrationResponse.
    This schema MUST NOT be used in any endpoint accessible without
    admin-role authentication.
    """

    model_config = _ADMIN_ORM

    # Public fields
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
    # Status
    status: CelebrationStatus
    completion_percentage: int
    # Financials
    currency: Currency
    estimated_budget: Decimal | None = None
    final_budget: Decimal | None = None
    special_instructions: str | None = None
    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Admin-only: NotesMixin / MetadataMixin
    internal_notes: str | None = Field(
        default=None,
        description="Internal team notes — ADMIN ONLY",
    )
    extra_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary JSON metadata for internal tooling — ADMIN ONLY",
    )

    # Admin-only: SoftDeleteMixin
    deleted_at: datetime | None = Field(
        default=None,
        description="Soft-deletion timestamp (null if record is live) — ADMIN ONLY",
    )


class CelebrationSummary(BaseSchema):
    """
    Lightweight celebration summary for admin list views and dashboards.

    Contains only the fields needed for a compact table row; avoids
    transmitting the full record when a list of hundreds of celebrations
    is displayed.
    """

    model_config = _ADMIN_ORM

    id: uuid.UUID
    customer_id: uuid.UUID = Field(description="FK to the owning customer")
    title: str = Field(description="Short celebration title")
    celebration_date: date = Field(description="Calendar date of the celebration")
    status: CelebrationStatus = Field(description="Current lifecycle status")
    completion_percentage: int = Field(
        ge=0,
        le=100,
        description="Planning progress percentage (0–100)",
    )
    guest_count: int = Field(description="Expected number of guests")
    estimated_budget: Decimal | None = Field(
        default=None, description="Planned total budget"
    )
