"""
Support Routes — tickets, messages, attachments, and assignment.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.support import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.support.response import (
    SupportAttachmentResponse,
    SupportMessageResponse,
    SupportTicketResponse,
)

router = APIRouter(prefix="/support", tags=["Support"])

# ── All tickets (staff view — static, must precede /tickets/{ticket_id}) ─────

router.add_api_route(
    "/tickets/all",
    ctrl.list_all_tickets,
    methods=["GET"],
    response_model=CursorPaginatedResponse[SupportTicketResponse],
    status_code=status.HTTP_200_OK,
    summary="List All Tickets (Staff)",
    description="Return a cursor-paginated, filterable list of all support tickets. Staff access required.",
    operation_id="support_list_all_tickets",
)

# ── Tickets ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/tickets",
    ctrl.list_tickets,
    methods=["GET"],
    response_model=CursorPaginatedResponse[SupportTicketResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Tickets",
    description="Return a cursor-paginated list of support tickets for the authenticated user.",
    operation_id="support_list_tickets",
)

router.add_api_route(
    "/tickets",
    ctrl.create_ticket,
    methods=["POST"],
    response_model=SuccessResponse[SupportTicketResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Support Ticket",
    description="Open a new support ticket for the authenticated user.",
    operation_id="support_create_ticket",
)

router.add_api_route(
    "/tickets/{ticket_id}",
    ctrl.get_ticket,
    methods=["GET"],
    response_model=SuccessResponse[SupportTicketResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Support Ticket",
    description="Return a single ticket by ID. Access is role-gated (owner, staff, admin).",
    operation_id="support_get_ticket",
)

router.add_api_route(
    "/tickets/{ticket_id}/status",
    ctrl.update_ticket_status,
    methods=["PATCH"],
    response_model=SuccessResponse[SupportTicketResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Ticket Status (Staff)",
    description="Update the status of a support ticket. Staff access required.",
    operation_id="support_update_ticket_status",
)

router.add_api_route(
    "/tickets/{ticket_id}/assignments/{assignee_id}",
    ctrl.assign_ticket,
    methods=["POST"],
    response_model=SuccessResponse[SupportTicketResponse],
    status_code=status.HTTP_200_OK,
    summary="Assign Ticket (Admin)",
    description="Assign a support ticket to a staff member. Admin access required.",
    operation_id="support_assign_ticket",
)

# ── Messages ──────────────────────────────────────────────────────────────────

router.add_api_route(
    "/tickets/{ticket_id}/messages",
    ctrl.list_messages,
    methods=["GET"],
    response_model=SuccessResponse[list[SupportMessageResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Ticket Messages",
    description="Return the full message thread for a support ticket (naturally bounded, not paginated).",
    operation_id="support_list_messages",
)

router.add_api_route(
    "/tickets/{ticket_id}/messages",
    ctrl.add_message,
    methods=["POST"],
    response_model=SuccessResponse[SupportMessageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Send Message",
    description="Send a new message in a support ticket thread.",
    operation_id="support_add_message",
)

router.add_api_route(
    "/tickets/{ticket_id}/messages/{message_id}",
    ctrl.get_message,
    methods=["GET"],
    response_model=SuccessResponse[SupportMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Message",
    description="Return a single message by ID within a support ticket.",
    operation_id="support_get_message",
)

# ── Attachments ───────────────────────────────────────────────────────────────

router.add_api_route(
    "/tickets/{ticket_id}/attachments",
    ctrl.list_attachments,
    methods=["GET"],
    response_model=SuccessResponse[list[SupportAttachmentResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Attachments",
    description="Return all attachments associated with a support ticket.",
    operation_id="support_list_attachments",
)

router.add_api_route(
    "/tickets/{ticket_id}/attachments",
    ctrl.add_attachment,
    methods=["POST"],
    response_model=SuccessResponse[SupportAttachmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Attachment",
    description="Attach a file to a support ticket. Accepts multipart/form-data.",
    operation_id="support_add_attachment",
)

router.add_api_route(
    "/tickets/{ticket_id}/attachments/{attachment_id}",
    ctrl.delete_attachment,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Attachment",
    description="Remove an attachment from a support ticket.",
    operation_id="support_delete_attachment",
)
