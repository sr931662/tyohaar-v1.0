"""
Support domain — update (patch) schemas.

Three distinct update schemas are provided to enforce access control:
- SupportTicketUpdate: limited fields for service layer
- SupportTicketAgentUpdate: agent-specific fields including internal_notes
- SupportMessageUpdate: read-receipt updates only
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.base import BaseSchema

__all__ = [
    "SupportTicketUpdate",
    "SupportTicketAgentUpdate",
    "SupportMessageUpdate",
]


class SupportTicketUpdate(BaseSchema):
    """
    General-purpose patch schema for support ticket lifecycle management.

    Used by the support service for automated state transitions
    (e.g., auto-close after resolution timeout).
    """

    assigned_agent_id: uuid.UUID | None = Field(
        default=None,
        description="Assign or reassign the ticket to an agent.",
    )
    category: str | None = Field(
        default=None,
        description="Updated ticket category after agent triage.",
    )
    priority: TicketPriority | None = Field(
        default=None,
        description="Updated priority after agent assessment.",
    )
    ticket_status: TicketStatus | None = Field(
        default=None,
        description="New lifecycle status.",
    )
    resolution_summary: str | None = Field(
        default=None,
        description="Customer-visible resolution description.",
    )
    sla_due_at: datetime | None = Field(
        default=None,
        description="Computed or overridden SLA deadline.",
    )
    first_response_at: datetime | None = Field(
        default=None,
        description="Timestamp of the first agent response.",
    )
    resolved_at: datetime | None = Field(
        default=None,
        description="Timestamp when the ticket was marked RESOLVED.",
    )
    closed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the ticket was moved to CLOSED state.",
    )
    last_activity_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent activity on the ticket.",
    )


class SupportTicketAgentUpdate(BaseSchema):
    """
    Agent and admin-only patch schema for support ticket management.

    Adds internal_notes which must never be visible to customers.
    This schema requires SUPPORT or ADMIN role at the router level.
    """

    ticket_status: TicketStatus | None = Field(
        default=None,
        description="Agent-initiated status transition.",
    )
    priority: TicketPriority | None = Field(
        default=None,
        description="Adjusted priority after investigation.",
    )
    assigned_agent_id: uuid.UUID | None = Field(
        default=None,
        description="Transfer to another agent.",
    )
    resolution_summary: str | None = Field(
        default=None,
        description="Customer-visible resolution text.",
    )
    internal_notes: str | None = Field(
        default=None,
        description="AGENT/ADMIN ONLY: Private notes not visible to the customer.",
    )


class SupportMessageUpdate(BaseSchema):
    """
    Read-receipt update schema for support message records.

    Only read flags may be updated; message content is immutable after creation.
    """

    is_read_by_customer: bool | None = Field(
        default=None,
        description="Set True when the customer has viewed this message.",
    )
    is_read_by_agent: bool | None = Field(
        default=None,
        description="Set True when an agent has viewed this message.",
    )


class SupportTicketStatusUpdate(BaseSchema):
    """Minimal status-only update for lightweight status-transition endpoints."""

    ticket_status: TicketStatus = Field(description="New status for the ticket.")
    resolution_summary: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional resolution summary when closing a ticket.",
    )
