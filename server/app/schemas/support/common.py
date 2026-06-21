"""
Support domain — shared types and enum re-exports.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import Field

from app.models.enums import TicketCategory, TicketPriority, TicketStatus
from app.schemas.base import BaseSchema

__all__ = [
    "TicketStatus",
    "TicketPriority",
    "TicketCategory",
    "TicketSLAStatus",
]


class TicketSLAStatus(BaseSchema):
    """
    SLA compliance status for a support ticket.

    Computed by the support service based on sla_due_at and current time.
    Surfaced in agent dashboards to highlight breached or at-risk tickets.
    """

    is_breached: bool = Field(
        description="True if current time has passed sla_due_at without resolution.",
    )
    is_at_risk: bool = Field(
        description="True if ticket will breach SLA within the next 2 hours.",
    )
    minutes_remaining: int | None = Field(
        default=None,
        description="Minutes until SLA breach. Negative if already breached.",
    )
    sla_tier: Literal["green", "amber", "red"] = Field(
        description="Traffic-light SLA health indicator for UI rendering.",
    )
