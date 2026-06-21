from __future__ import annotations

from uuid import UUID

from app.models.enums import TicketStatus
from app.models.support.ticket import SupportTicket
from app.repositories.unit_of_work import UnitOfWork
from app.services.support.constants import MAX_MESSAGES_PER_TICKET, MAX_OPEN_TICKETS_PER_USER
from app.services.support.exceptions import (
    OpenTicketLimitError,
    TicketNotFoundError,
    TicketOwnershipError,
    TicketStatusTransitionError,
)
from app.services.support.helpers import is_ticket_status_transition_valid

_STAFF_ROLES = {"support", "admin", "agent"}
_OPEN_STATUSES = {TicketStatus.OPEN, TicketStatus.PENDING, TicketStatus.IN_PROGRESS}


async def validate_ticket_exists(
    ticket_id: UUID,
    uow: UnitOfWork,
) -> SupportTicket:
    ticket = await uow.support.tickets.get_by_id(ticket_id)
    if ticket is None:
        raise TicketNotFoundError(str(ticket_id))
    return ticket


async def validate_ticket_ownership(
    ticket_id: UUID,
    user_id: UUID,
    uow: UnitOfWork,
    role: str = "customer",
) -> SupportTicket:
    ticket = await uow.support.tickets.get_by_id(ticket_id)
    if ticket is None:
        raise TicketNotFoundError(str(ticket_id))
    if role.lower() in _STAFF_ROLES:
        return ticket
    if ticket.customer_id != user_id:
        raise TicketOwnershipError()
    return ticket


def validate_ticket_status_transition(
    ticket: SupportTicket,
    new_status: str,
) -> None:
    current = ticket.ticket_status.value if hasattr(ticket.ticket_status, "value") else str(ticket.ticket_status)
    if not is_ticket_status_transition_valid(current, new_status):
        raise TicketStatusTransitionError(
            f"Transition from '{current}' to '{new_status}' is not allowed."
        )


async def validate_open_ticket_limit(user_id: UUID, uow: UnitOfWork) -> None:
    from app.models.support.ticket import SupportTicket as ST
    open_tickets = await uow.support.tickets.find_many(
        ST.customer_id == user_id,
        ST.ticket_status.in_(list(_OPEN_STATUSES)),
    )
    if len(open_tickets) >= MAX_OPEN_TICKETS_PER_USER:
        raise OpenTicketLimitError(
            f"Maximum {MAX_OPEN_TICKETS_PER_USER} open tickets per user."
        )


async def validate_message_count(ticket_id: UUID, uow: UnitOfWork) -> None:
    from app.models.support.message import SupportMessage as SM
    count = await uow.support.messages.count(SM.ticket_id == ticket_id)
    if count >= MAX_MESSAGES_PER_TICKET:
        from app.services.support.exceptions import TicketClosedError
        from app.services.exceptions import BusinessRuleError
        raise BusinessRuleError(
            f"Ticket has reached the maximum of {MAX_MESSAGES_PER_TICKET} messages."
        )
