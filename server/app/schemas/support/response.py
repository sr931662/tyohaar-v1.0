"""
Support domain — response (output) schemas.

Security rules enforced here:
- SupportTicketResponse (customer): NO internal_notes, NO deleted_at
- SupportTicketAgentResponse (agent/admin): ADDS internal_notes
- SupportMessageResponse: is_internal field excluded (service layer filters internal messages)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.models.enums import TicketCategory, TicketPriority, TicketStatus
from app.schemas.base import BaseSchema

__all__ = [
    "SupportTicketResponse",
    "SupportTicketAgentResponse",
    "SupportMessageResponse",
    "SupportAttachmentResponse",
]


class SupportTicketResponse(BaseSchema):
    """
    Customer-facing support ticket view.

    Excludes: internal_notes (agent-only), deleted_at (audit-only).
    The service layer MUST filter is_internal=True messages before returning
    the message thread to a customer.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    ticket_number: str = Field(description="Human-readable ticket ID, e.g. TKT-2024-001234.")
    customer_id: uuid.UUID
    assigned_agent_id: uuid.UUID | None = None
    booking_id: uuid.UUID | None = None
    payment_id: uuid.UUID | None = None
    category: TicketCategory
    priority: TicketPriority
    ticket_status: TicketStatus
    subject: str
    description: str
    resolution_summary: str | None = None
    sla_due_at: datetime | None = None
    first_response_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    last_activity_at: datetime | None = None
    reopened_count: int
    created_at: datetime
    # NOTE: internal_notes and deleted_at intentionally omitted


class SupportTicketAgentResponse(SupportTicketResponse):
    """
    Agent and admin view of a support ticket.

    Extends the customer view with internal_notes which are private
    agent commentary not visible to the ticket owner.
    Requires SUPPORT or ADMIN role.
    """

    internal_notes: str | None = Field(
        default=None,
        description="Private agent notes. Must never be exposed to customers.",
    )


class SupportMessageResponse(BaseSchema):
    """
    Support message record returned in the ticket thread endpoint.

    is_internal field is excluded because the service layer must filter out
    internal messages before returning the thread to a customer caller.
    Agents receive is_internal messages via a separate agent-only endpoint.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    sender_id: uuid.UUID
    message_type: str
    body: str
    is_read_by_customer: bool
    is_read_by_agent: bool
    created_at: datetime
    # NOTE: is_internal intentionally omitted


class SupportAttachmentResponse(BaseSchema):
    """
    File attachment record associated with a support ticket or message.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    message_id: uuid.UUID | None = None
    uploaded_by_id: uuid.UUID
    file_name: str
    file_url: str
    file_type: str
    file_size_bytes: int | None = None
    created_at: datetime
