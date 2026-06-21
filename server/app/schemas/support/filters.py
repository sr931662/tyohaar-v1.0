"""
Support domain — filter query parameter schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import TicketCategory, TicketPriority, TicketStatus
from app.schemas.base import BaseSchema

__all__ = [
    "SupportTicketFilters",
]


class SupportTicketFilters(BaseSchema):
    """
    Filter parameters for the support ticket list endpoint.

    Used by both the customer 'my tickets' view (pre-filtered to customer_id)
    and the agent queue view (full filter capability).

    The `search` field performs a partial match against ticket_number and subject.
    """

    customer_id: uuid.UUID | None = Field(
        default=None,
        description="Filter tickets belonging to a specific customer.",
    )
    assigned_agent_id: uuid.UUID | None = Field(
        default=None,
        description="Filter tickets assigned to a specific agent.",
    )
    category: TicketCategory | None = Field(
        default=None,
        description="Filter by ticket category.",
    )
    priority: TicketPriority | None = Field(
        default=None,
        description="Filter by ticket priority.",
    )
    ticket_status: TicketStatus | None = Field(
        default=None,
        description="Filter by ticket lifecycle status.",
    )
    booking_id: uuid.UUID | None = Field(
        default=None,
        description="Filter tickets linked to a specific booking.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Include only tickets created at or after this timestamp.",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Include only tickets created at or before this timestamp.",
    )
    search: str | None = Field(
        default=None,
        max_length=200,
        description="Partial text match against ticket_number and subject fields.",
    )
