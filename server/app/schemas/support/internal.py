"""
Support domain — internal / admin-only schemas.

Includes full ticket details with soft-delete state, and aggregated
dashboard statistics for the support operations team.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.models.enums import TicketCategory, TicketPriority, TicketStatus
from app.schemas.base import BaseSchema
from app.schemas.support.response import SupportTicketAgentResponse

__all__ = [
    "SupportTicketInternal",
    "SupportTicketAdminSummary",
]


class SupportTicketInternal(SupportTicketAgentResponse):
    """
    Complete ticket record for admin tools and data export.

    Adds soft-delete state and full audit timestamps.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    deleted_at: datetime | None = Field(
        default=None,
        description="Soft-delete timestamp. None means the ticket is live.",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last modification timestamp from the TimestampMixin.",
    )


class SupportTicketAdminSummary(BaseSchema):
    """
    Aggregated support dashboard statistics.

    Computed by the support analytics service and cached in Redis.
    Displayed in the admin panel's support overview page.
    """

    total_open: int = Field(description="Count of tickets in OPEN status.")
    total_in_progress: int = Field(description="Count of tickets IN_PROGRESS.")
    total_waiting_on_customer: int = Field(description="Count in WAITING_ON_CUSTOMER.")
    total_waiting_on_vendor: int = Field(description="Count in WAITING_ON_VENDOR.")
    total_escalated: int = Field(description="Count of ESCALATED tickets.")
    total_resolved_today: int = Field(description="Tickets resolved in the last 24 hours.")
    total_sla_breached: int = Field(description="Open tickets that have exceeded sla_due_at.")
    total_sla_at_risk: int = Field(
        description="Open tickets within 2 hours of SLA breach.",
    )
    avg_first_response_minutes: float | None = Field(
        default=None,
        description="Average time-to-first-response in minutes over the last 30 days.",
    )
    avg_resolution_hours: float | None = Field(
        default=None,
        description="Average ticket resolution time in hours over the last 30 days.",
    )
    tickets_by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of open ticket count by TicketCategory value.",
    )
    tickets_by_priority: dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of open ticket count by TicketPriority value.",
    )
    as_of: datetime = Field(
        description="Timestamp when this summary was computed.",
    )
