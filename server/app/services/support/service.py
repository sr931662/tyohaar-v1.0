from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import TicketStatus
from app.models.support.message import SupportMessage, SupportSenderRole
from app.models.support.ticket import SupportTicket
from app.schemas.base import CursorPage
from app.schemas.support.create import (
    SupportMessageCreate,
    SupportTicketCreate,
)
from app.schemas.support.filters import SupportTicketFilters
from app.schemas.support.update import SupportTicketStatusUpdate
from app.schemas.support.response import (
    SupportAttachmentResponse,
    SupportMessageResponse,
    SupportTicketResponse,
)
from app.services.base import BaseService
from app.services.support.constants import MAX_ATTACHMENTS_PER_MESSAGE
from app.services.support.exceptions import (
    AttachmentLimitError,
    AttachmentNotFoundError,
    MessageNotFoundError,
    TicketClosedError,
    TicketNotFoundError,
)
from app.services.support.helpers import generate_ticket_number
from app.services.support.validators import (
    validate_message_count,
    validate_open_ticket_limit,
    validate_ticket_exists,
    validate_ticket_ownership,
    validate_ticket_status_transition,
)

logger = logging.getLogger(__name__)

_STAFF_ROLES = {"support", "admin", "super_admin", "agent"}


class SupportService(BaseService):
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    ) -> None:
        super().__init__(session_factory)

    # ── Ticket Lifecycle ──────────────────────────────────────────────────────

    async def create_ticket(
        self,
        user_id: UUID,
        data: SupportTicketCreate,
    ) -> SupportTicketResponse:
        async with self._uow() as uow:
            await validate_open_ticket_limit(user_id, uow)
            ticket_number = generate_ticket_number()

            ticket = await uow.support.tickets.create_from_dict({
                "ticket_number": ticket_number,
                "customer_id": user_id,
                "category": data.category,
                "priority": data.priority,
                "subject": data.subject,
                "description": data.description,
                "booking_id": data.booking_id,
                "payment_id": data.payment_id,
                "ticket_status": TicketStatus.OPEN,
                "last_activity_at": datetime.now(tz=timezone.utc),
                "reopened_count": 0,
            })
            await uow.commit()
            return SupportTicketResponse.model_validate(ticket)

    async def get_ticket(
        self,
        ticket_id: UUID,
        requester_id: UUID,
        requester_role: str,
    ) -> SupportTicketResponse:
        async with self._uow() as uow:
            ticket = await validate_ticket_ownership(
                ticket_id, requester_id, uow, role=requester_role
            )
            return SupportTicketResponse.model_validate(ticket)

    @staticmethod
    def _build_filter_conditions(filters: SupportTicketFilters) -> list:
        conditions = []
        if filters.category is not None:
            conditions.append(SupportTicket.category == filters.category)
        if filters.priority is not None:
            conditions.append(SupportTicket.priority == filters.priority)
        if filters.ticket_status is not None:
            conditions.append(SupportTicket.ticket_status == filters.ticket_status)
        if filters.assigned_agent_id is not None:
            conditions.append(SupportTicket.assigned_agent_id == filters.assigned_agent_id)
        if filters.booking_id is not None:
            conditions.append(SupportTicket.booking_id == filters.booking_id)
        if filters.from_date is not None:
            conditions.append(SupportTicket.created_at >= filters.from_date)
        if filters.to_date is not None:
            conditions.append(SupportTicket.created_at <= filters.to_date)
        if filters.search:
            from sqlalchemy import or_
            conditions.append(
                or_(
                    SupportTicket.ticket_number.ilike(f"%{filters.search}%"),
                    SupportTicket.subject.ilike(f"%{filters.search}%"),
                )
            )
        return conditions

    async def list_tickets(
        self,
        user_id: UUID,
        filters: SupportTicketFilters,
        cursor: str | None,
        limit: int,
    ) -> CursorPage[SupportTicketResponse]:
        async with self._uow() as uow:
            conditions = [SupportTicket.customer_id == user_id, *self._build_filter_conditions(filters)]
            page = await uow.support.tickets.cursor_paginate(
                *conditions,
                cursor=cursor,
                limit=limit,
            )
            return CursorPage(
                items=[SupportTicketResponse.model_validate(t) for t in page.items],
                next_cursor=page.next_cursor,
                page_size=page.page_size,
            )

    async def list_all_tickets(
        self,
        filters: SupportTicketFilters,
        cursor: str | None,
        limit: int,
    ) -> CursorPage[SupportTicketResponse]:
        async with self._uow() as uow:
            conditions = self._build_filter_conditions(filters)
            page = await uow.support.tickets.cursor_paginate(
                *conditions,
                cursor=cursor,
                limit=limit,
            )
            return CursorPage(
                items=[SupportTicketResponse.model_validate(t) for t in page.items],
                next_cursor=page.next_cursor,
                page_size=page.page_size,
            )

    async def update_ticket_status(
        self,
        ticket_id: UUID,
        updated_by_id: UUID,
        updated_by_role: str,
        data: SupportTicketStatusUpdate,
    ) -> SupportTicketResponse:
        new_status = data.ticket_status.value
        async with self._uow() as uow:
            ticket = await validate_ticket_exists(ticket_id, uow)
            validate_ticket_status_transition(ticket, new_status)

            now = datetime.now(tz=timezone.utc)
            update_data: dict = {
                "ticket_status": new_status,
                "last_activity_at": now,
            }
            if data.resolution_summary is not None:
                update_data["resolution_summary"] = data.resolution_summary

            status_lower = new_status.lower()
            if status_lower == "resolved":
                update_data["resolved_at"] = now
            elif status_lower == "closed":
                update_data["closed_at"] = now
            elif status_lower == "open":
                current = ticket.ticket_status.value if hasattr(ticket.ticket_status, "value") else str(ticket.ticket_status)
                if current in ("resolved", "closed"):
                    update_data["reopened_count"] = ticket.reopened_count + 1

            updated = await uow.support.tickets.update(ticket, update_data)
            await uow.commit()
            return SupportTicketResponse.model_validate(updated)

    async def assign_ticket(
        self,
        ticket_id: UUID,
        assignee_id: UUID,
        admin_id: UUID,
    ) -> SupportTicketResponse:
        async with self._uow() as uow:
            ticket = await validate_ticket_exists(ticket_id, uow)
            updated = await uow.support.tickets.update(ticket, {
                "assigned_agent_id": assignee_id,
                "last_activity_at": datetime.now(tz=timezone.utc),
            })
            await uow.commit()
            return SupportTicketResponse.model_validate(updated)

    # ── Messages ──────────────────────────────────────────────────────────────

    async def add_message(
        self,
        ticket_id: UUID,
        sender_id: UUID,
        sender_role: str,
        data: SupportMessageCreate,
    ) -> SupportMessageResponse:
        async with self._uow() as uow:
            ticket = await validate_ticket_exists(ticket_id, uow)

            current_status = (
                ticket.ticket_status.value
                if hasattr(ticket.ticket_status, "value")
                else str(ticket.ticket_status)
            )
            if current_status.lower() == "closed":
                raise TicketClosedError()

            await validate_message_count(ticket_id, uow)

            # Internal notes only allowed for staff roles
            is_internal = getattr(data, "is_internal", False) or getattr(data, "is_internal_note", False)
            if sender_role.lower() not in _STAFF_ROLES:
                is_internal = False

            # Map sender_role string to enum
            _role_map = {
                "customer": SupportSenderRole.CUSTOMER,
                "vendor": SupportSenderRole.CUSTOMER,
                "agent": SupportSenderRole.AGENT,
                "support": SupportSenderRole.AGENT,
                "admin": SupportSenderRole.ADMIN,
                "super_admin": SupportSenderRole.ADMIN,
                "system": SupportSenderRole.SYSTEM,
            }
            sender_role_enum = _role_map.get(sender_role.lower(), SupportSenderRole.CUSTOMER)

            message = await uow.support.messages.create_from_dict({
                "ticket_id": ticket_id,
                "sender_id": sender_id,
                "sender_role": sender_role_enum,
                "body": data.body,
                "is_internal_note": is_internal,
            })

            is_staff_reply = sender_role.lower() in _STAFF_ROLES and not is_internal
            ticket_update: dict = {"last_activity_at": datetime.now(tz=timezone.utc)}
            if is_staff_reply and ticket.first_response_at is None:
                ticket_update["first_response_at"] = datetime.now(tz=timezone.utc)
            await uow.support.tickets.update(ticket, ticket_update)

            notify_user_id = None
            if is_staff_reply:
                # Agent/admin replied — let the customer know.
                notify_user_id = ticket.customer_id
            elif not is_internal and ticket.assigned_agent_id is not None:
                # Customer replied on an assigned ticket — nudge the agent.
                notify_user_id = ticket.assigned_agent_id

            await uow.commit()
            response = SupportMessageResponse.model_validate(message)

        if notify_user_id is not None:
            await self._notify_new_message(notify_user_id, ticket, message)

        return response

    async def _notify_new_message(self, recipient_id: UUID, ticket: SupportTicket, message: SupportMessage) -> None:
        # Best-effort — a notification failure must never fail the reply itself.
        try:
            from app.models.enums import NotificationChannel, NotificationType
            from app.schemas.notifications.create import NotificationCreate
            from app.services.notifications.service import NotificationService

            await NotificationService().send_notification(
                user_id=recipient_id,
                data=NotificationCreate(
                    user_id=recipient_id,
                    notification_type=NotificationType.SUPPORT_UPDATE,
                    channel=NotificationChannel.IN_APP,
                    title=f"New reply on {ticket.ticket_number}",
                    body=message.body[:200],
                    reference_type="support_ticket",
                    reference_id=ticket.id,
                ),
            )
        except Exception:
            logger.exception("Failed to send support reply notification for ticket %s", ticket.id)

    async def list_messages(
        self,
        ticket_id: UUID,
        requester_id: UUID,
        requester_role: str,
    ) -> list[SupportMessageResponse]:
        async with self._uow() as uow:
            await validate_ticket_ownership(ticket_id, requester_id, uow, role=requester_role)

            if requester_role.lower() in _STAFF_ROLES:
                messages = await uow.support.messages.find_by_ticket(ticket_id)
            else:
                # Filter out internal notes for customers
                messages = await uow.support.messages.find_public_for_ticket(ticket_id)

            return [SupportMessageResponse.model_validate(m) for m in messages]

    async def get_message(
        self,
        ticket_id: UUID,
        message_id: UUID,
        requester_id: UUID,
        requester_role: str,
    ) -> SupportMessageResponse:
        async with self._uow() as uow:
            await validate_ticket_ownership(ticket_id, requester_id, uow, role=requester_role)

            message = await uow.support.messages.get_by_id(message_id)
            if message is None or message.ticket_id != ticket_id:
                raise MessageNotFoundError(str(message_id))

            # Customers must not see internal notes
            if requester_role.lower() not in _STAFF_ROLES and message.is_internal_note:
                raise MessageNotFoundError(str(message_id))

            return SupportMessageResponse.model_validate(message)

    # ── Attachments ───────────────────────────────────────────────────────────
    #
    # Attachments here are ticket-scoped (message_id=NULL) — the public routes
    # are POST/GET /tickets/{ticket_id}/attachments with no message in the
    # path. The model documents this as a valid state for files uploaded
    # before any message exists (see SupportAttachment docstring).

    async def add_attachment(
        self,
        ticket_id: UUID,
        requester_id: UUID,
        requester_role: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> SupportAttachmentResponse:
        async with self._uow() as uow:
            await validate_ticket_ownership(ticket_id, requester_id, uow, role=requester_role)

            existing = await uow.support.attachments.find_by_ticket(ticket_id)
            if len(existing) >= MAX_ATTACHMENTS_PER_MESSAGE:
                raise AttachmentLimitError(
                    f"A ticket may have at most {MAX_ATTACHMENTS_PER_MESSAGE} attachments."
                )

            from app.models.enums import MediaType
            from app.services.media.cloudinary_client import upload_image_bytes

            content_type = content_type or "application/octet-stream"
            is_image = content_type.startswith("image/")
            if is_image:
                media_type = MediaType.IMAGE
            elif content_type.startswith("video/"):
                media_type = MediaType.VIDEO
            elif content_type.startswith("audio/"):
                media_type = MediaType.AUDIO
            else:
                media_type = MediaType.DOCUMENT

            result = await upload_image_bytes(
                file_bytes,
                folder="tyohaar/support_attachments",
                resource_type="image" if is_image else "raw",
            )

            attachment = await uow.support.attachments.create_from_dict({
                "ticket_id": ticket_id,
                "message_id": None,
                "uploaded_by_id": requester_id,
                "media_type": media_type,
                "mime_type": content_type,
                "filename": filename,
                "storage_key": result["public_id"],
                "storage_url": result["secure_url"],
                "file_size_bytes": result.get("bytes") or len(file_bytes),
                "uploaded_at": datetime.now(tz=timezone.utc),
            })
            await uow.commit()
            return SupportAttachmentResponse.model_validate(attachment)

    async def list_attachments(
        self,
        ticket_id: UUID,
        requester_id: UUID,
        requester_role: str,
    ) -> list[SupportAttachmentResponse]:
        async with self._uow() as uow:
            await validate_ticket_ownership(ticket_id, requester_id, uow, role=requester_role)
            attachments = await uow.support.attachments.find_by_ticket(ticket_id)
            return [SupportAttachmentResponse.model_validate(a) for a in attachments]

    async def delete_attachment(
        self,
        ticket_id: UUID,
        attachment_id: UUID,
        requester_id: UUID,
        requester_role: str,
    ) -> None:
        async with self._uow() as uow:
            await validate_ticket_ownership(ticket_id, requester_id, uow, role=requester_role)

            attachment = await uow.support.attachments.get_by_id(attachment_id)
            if attachment is None or attachment.ticket_id != ticket_id:
                raise AttachmentNotFoundError(str(attachment_id))

            is_staff = requester_role.lower() in _STAFF_ROLES
            if not is_staff and attachment.uploaded_by_id != requester_id:
                from app.services.exceptions import PermissionError
                raise PermissionError("You do not have permission to delete this attachment.")

            await uow.support.attachments.delete(attachment)
            await uow.commit()
