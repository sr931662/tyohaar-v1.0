"""
Support Controller — tickets, messages, attachments, and assignment.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, UploadFile

from app.core.current_user import CurrentUserDep
from app.core.dependencies import SupportServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep, StaffDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.support.create import (
    SupportMessageCreate,
    SupportTicketCreate,
)
from app.schemas.support.filters import SupportTicketFilters
from app.schemas.support.response import (
    SupportAttachmentResponse,
    SupportMessageResponse,
    SupportTicketResponse,
)
from app.schemas.support.update import SupportTicketStatusUpdate


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


# ── Tickets ───────────────────────────────────────────────────────────────────

async def create_ticket(
    body: SupportTicketCreate,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
) -> SuccessResponse[SupportTicketResponse]:
    result = await service.create_ticket(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Support ticket created.")


async def get_ticket(
    ticket_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
) -> SuccessResponse[SupportTicketResponse]:
    result = await service.get_ticket(
        ticket_id=ticket_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=result, message="Ticket retrieved.")


async def list_tickets(
    current_user: CurrentUserDep,
    filters: Annotated[SupportTicketFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: SupportServiceDep,
) -> CursorPaginatedResponse[SupportTicketResponse]:
    page = await service.list_tickets(
        user_id=current_user.id,
        filters=filters,
        cursor=pagination.cursor,
        limit=pagination.page_size,
    )
    return _cursor_resp(page, pagination.page_size)


async def list_all_tickets(
    filters: Annotated[SupportTicketFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    _staff: StaffDep,
    service: SupportServiceDep,
) -> CursorPaginatedResponse[SupportTicketResponse]:
    page = await service.list_all_tickets(
        filters=filters, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def update_ticket_status(
    ticket_id: uuid.UUID,
    body: SupportTicketStatusUpdate,
    current_user: StaffDep,
    service: SupportServiceDep,
) -> SuccessResponse[SupportTicketResponse]:
    result = await service.update_ticket_status(
        ticket_id=ticket_id,
        updated_by_id=current_user.id,
        updated_by_role=current_user.role.value,
        data=body,
    )
    return SuccessResponse(data=result, message="Ticket status updated.")


async def assign_ticket(
    ticket_id: uuid.UUID,
    assignee_id: uuid.UUID,
    current_user: AdminDep,
    service: SupportServiceDep,
) -> SuccessResponse[SupportTicketResponse]:
    result = await service.assign_ticket(
        ticket_id=ticket_id, assignee_id=assignee_id, admin_id=current_user.id
    )
    return SuccessResponse(data=result, message="Ticket assigned.")


# ── Messages ──────────────────────────────────────────────────────────────────

async def add_message(
    ticket_id: uuid.UUID,
    body: SupportMessageCreate,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
) -> SuccessResponse[SupportMessageResponse]:
    result = await service.add_message(
        ticket_id=ticket_id,
        sender_id=current_user.id,
        sender_role=current_user.role.value,
        data=body,
    )
    return SuccessResponse(data=result, message="Message sent.")


async def list_messages(
    ticket_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
) -> SuccessResponse[list[SupportMessageResponse]]:
    # A ticket's thread is naturally bounded (MAX_MESSAGES_PER_TICKET) — the
    # service returns the full list rather than a cursor page.
    messages = await service.list_messages(
        ticket_id=ticket_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=messages, message="Messages retrieved.")


async def get_message(
    ticket_id: uuid.UUID,
    message_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
) -> SuccessResponse[SupportMessageResponse]:
    result = await service.get_message(
        ticket_id=ticket_id,
        message_id=message_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=result, message="Message retrieved.")


# ── Attachments ───────────────────────────────────────────────────────────────

async def add_attachment(
    ticket_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
    file: UploadFile,
) -> SuccessResponse[SupportAttachmentResponse]:
    content = await file.read()
    result = await service.add_attachment(
        ticket_id=ticket_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
        file_bytes=content,
        filename=file.filename or "attachment",
        content_type=file.content_type or "application/octet-stream",
    )
    return SuccessResponse(data=result, message="Attachment uploaded.")


async def list_attachments(
    ticket_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
) -> SuccessResponse[list[SupportAttachmentResponse]]:
    attachments = await service.list_attachments(
        ticket_id=ticket_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=attachments, message="Attachments retrieved.")


async def delete_attachment(
    ticket_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: SupportServiceDep,
) -> SuccessResponse[None]:
    await service.delete_attachment(
        ticket_id=ticket_id,
        attachment_id=attachment_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=None, message="Attachment deleted.")
