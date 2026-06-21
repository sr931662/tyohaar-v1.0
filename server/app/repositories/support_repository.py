"""
Support repository — SupportTicket, SupportMessage, SupportAttachment.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import TicketCategory, TicketPriority, TicketStatus
from app.models.support.attachment import SupportAttachment
from app.models.support.message import SupportMessage
from app.models.support.ticket import SupportTicket
from app.repositories.base import BaseRepository


class SupportTicketRepository(BaseRepository[SupportTicket]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SupportTicket)

    async def find_by_number(self, ticket_number: str) -> SupportTicket | None:
        return await self.find_one(SupportTicket.ticket_number == ticket_number)

    async def find_by_customer(
        self,
        customer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[SupportTicket]:
        return await self.find_many(
            SupportTicket.customer_id == customer_id,
            order_by=SupportTicket.last_activity_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_agent(
        self,
        agent_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[SupportTicket]:
        return await self.find_many(
            SupportTicket.assigned_agent_id == agent_id,
            order_by=SupportTicket.last_activity_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_unassigned(self, *, skip: int = 0, limit: int = 50) -> list[SupportTicket]:
        return await self.find_many(
            SupportTicket.assigned_agent_id.is_(None),
            SupportTicket.ticket_status.in_([
                TicketStatus.OPEN,
                TicketStatus.PENDING,
            ]),
            order_by=SupportTicket.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_open(self, *, skip: int = 0, limit: int = 100) -> list[SupportTicket]:
        return await self.find_many(
            SupportTicket.ticket_status.in_([
                TicketStatus.OPEN,
                TicketStatus.PENDING,
                TicketStatus.IN_PROGRESS,
            ]),
            order_by=SupportTicket.last_activity_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_status(
        self,
        status: TicketStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SupportTicket]:
        return await self.find_many(
            SupportTicket.ticket_status == status,
            order_by=SupportTicket.last_activity_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_priority(
        self,
        priority: TicketPriority,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SupportTicket]:
        return await self.find_many(
            SupportTicket.priority == priority,
            SupportTicket.ticket_status.not_in([
                TicketStatus.RESOLVED,
                TicketStatus.CLOSED,
            ]),
            order_by=SupportTicket.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_category(
        self,
        category: TicketCategory,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SupportTicket]:
        return await self.find_many(
            SupportTicket.category == category,
            skip=skip,
            limit=limit,
        )

    async def find_sla_breached(self) -> list[SupportTicket]:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            SupportTicket.sla_due_at < now,
            SupportTicket.first_response_at.is_(None),
            SupportTicket.ticket_status.not_in([
                TicketStatus.RESOLVED,
                TicketStatus.CLOSED,
            ]),
            order_by=SupportTicket.sla_due_at.asc(),
        )

    async def find_by_booking(self, booking_id: uuid.UUID) -> list[SupportTicket]:
        return await self.find_many(SupportTicket.booking_id == booking_id)

    async def find_by_payment(self, payment_id: uuid.UUID) -> list[SupportTicket]:
        return await self.find_many(SupportTicket.payment_id == payment_id)

    async def get_with_messages(self, ticket_id: uuid.UUID) -> SupportTicket | None:
        return await self.get_by_id(
            ticket_id,
            options=[selectinload(SupportTicket.messages)],
        )

    async def get_full(self, ticket_id: uuid.UUID) -> SupportTicket | None:
        return await self.get_by_id(
            ticket_id,
            options=[
                selectinload(SupportTicket.messages).selectinload(SupportMessage.attachments),
            ],
        )


class SupportMessageRepository(BaseRepository[SupportMessage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SupportMessage)

    async def find_by_ticket(
        self,
        ticket_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SupportMessage]:
        return await self.find_many(
            SupportMessage.ticket_id == ticket_id,
            order_by=SupportMessage.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_public_for_ticket(self, ticket_id: uuid.UUID) -> list[SupportMessage]:
        return await self.find_many(
            SupportMessage.ticket_id == ticket_id,
            SupportMessage.is_internal_note == False,  # noqa: E712
            order_by=SupportMessage.created_at.asc(),
        )

    async def find_internal_notes(self, ticket_id: uuid.UUID) -> list[SupportMessage]:
        return await self.find_many(
            SupportMessage.ticket_id == ticket_id,
            SupportMessage.is_internal_note == True,  # noqa: E712
            order_by=SupportMessage.created_at.asc(),
        )

    async def get_first_agent_reply(self, ticket_id: uuid.UUID) -> SupportMessage | None:
        return await self.find_one(
            SupportMessage.ticket_id == ticket_id,
            SupportMessage.sender_role == "agent",
            SupportMessage.is_internal_note == False,  # noqa: E712
        )


class SupportAttachmentRepository(BaseRepository[SupportAttachment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SupportAttachment)

    async def find_by_ticket(self, ticket_id: uuid.UUID) -> list[SupportAttachment]:
        return await self.find_many(SupportAttachment.ticket_id == ticket_id)

    async def find_by_message(self, message_id: uuid.UUID) -> list[SupportAttachment]:
        return await self.find_many(SupportAttachment.message_id == message_id)


class SupportRepositoryAggregate:
    """Groups support-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.tickets = SupportTicketRepository(session)
        self.messages = SupportMessageRepository(session)
        self.attachments = SupportAttachmentRepository(session)
