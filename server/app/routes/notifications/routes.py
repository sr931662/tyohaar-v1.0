"""
Notifications Routes — send, list, read, preferences, and templates.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.notifications import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.notifications.response import (
    NotificationPreferencesResponse,
    NotificationResponse,
    NotificationTemplateResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# ── Preferences (static — must precede /{notification_id}) ───────────────────

router.add_api_route(
    "/preferences",
    ctrl.get_preferences,
    methods=["GET"],
    response_model=SuccessResponse[NotificationPreferencesResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Notification Preferences",
    description="Return the notification channel preferences for the authenticated user.",
    operation_id="notifications_get_preferences",
)

router.add_api_route(
    "/preferences",
    ctrl.update_preferences,
    methods=["PUT"],
    response_model=SuccessResponse[NotificationPreferencesResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Notification Preferences",
    description="Update notification channel preferences for the authenticated user.",
    operation_id="notifications_update_preferences",
)

# ── Unread count (static) ─────────────────────────────────────────────────────

router.add_api_route(
    "/unread-count",
    ctrl.get_unread_count,
    methods=["GET"],
    response_model=SuccessResponse[int],
    status_code=status.HTTP_200_OK,
    summary="Get Unread Count",
    description="Return the total number of unread notifications for the authenticated user.",
    operation_id="notifications_get_unread_count",
)

# ── Mark all read (static) ────────────────────────────────────────────────────

router.add_api_route(
    "/mark-all-read",
    ctrl.mark_all_read,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Mark All Notifications Read",
    description="Mark every unread notification as read for the authenticated user.",
    operation_id="notifications_mark_all_read",
)

# ── Admin — send ──────────────────────────────────────────────────────────────

router.add_api_route(
    "/send",
    ctrl.send_notification,
    methods=["POST"],
    response_model=SuccessResponse[NotificationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Send Notification (Admin)",
    description="Send a direct notification to a specific user. Admin access required.",
    operation_id="notifications_send_notification",
)

router.add_api_route(
    "/template/send",
    ctrl.send_from_template,
    methods=["POST"],
    response_model=SuccessResponse[NotificationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Send From Template (Admin)",
    description="Send a notification rendered from a template. Admin access required.",
    operation_id="notifications_send_from_template",
)

router.add_api_route(
    "/broadcast",
    ctrl.broadcast_notification,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Broadcast Notification (Admin)",
    description="Enqueue a mass notification to all users or a filtered segment. Admin access required.",
    operation_id="notifications_broadcast_notification",
)

# ── Admin — templates ─────────────────────────────────────────────────────────

router.add_api_route(
    "/templates",
    ctrl.list_templates,
    methods=["GET"],
    response_model=SuccessResponse[list[NotificationTemplateResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Templates (Admin)",
    description="Return all notification templates. Admin access required.",
    operation_id="notifications_list_templates",
)

router.add_api_route(
    "/templates",
    ctrl.create_template,
    methods=["POST"],
    response_model=SuccessResponse[NotificationTemplateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Template (Admin)",
    description="Create a new notification template. Admin access required.",
    operation_id="notifications_create_template",
)

router.add_api_route(
    "/templates/{template_id}",
    ctrl.get_template,
    methods=["GET"],
    response_model=SuccessResponse[NotificationTemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Template (Admin)",
    description="Return a single notification template by ID. Admin access required.",
    operation_id="notifications_get_template",
)

router.add_api_route(
    "/templates/{template_id}",
    ctrl.update_template,
    methods=["PUT"],
    response_model=SuccessResponse[NotificationTemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Template (Admin)",
    description="Update an existing notification template. Admin access required.",
    operation_id="notifications_update_template",
)

router.add_api_route(
    "/templates/{template_id}",
    ctrl.delete_template,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Template (Admin)",
    description="Delete a notification template. Admin access required.",
    operation_id="notifications_delete_template",
)

# ── User notification list ────────────────────────────────────────────────────

router.add_api_route(
    "",
    ctrl.list_notifications,
    methods=["GET"],
    response_model=CursorPaginatedResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Notifications",
    description="Return a cursor-paginated list of notifications for the authenticated user.",
    operation_id="notifications_list_notifications",
)

router.add_api_route(
    "/{notification_id}",
    ctrl.get_notification,
    methods=["GET"],
    response_model=SuccessResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Notification",
    description="Return a single notification by ID. User ownership required.",
    operation_id="notifications_get_notification",
)

router.add_api_route(
    "/{notification_id}/read",
    ctrl.mark_read,
    methods=["PATCH"],
    response_model=SuccessResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark Notification Read",
    description="Mark a specific notification as read.",
    operation_id="notifications_mark_read",
)

router.add_api_route(
    "/{notification_id}",
    ctrl.delete_notification,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Notification",
    description="Delete a notification from the user's inbox.",
    operation_id="notifications_delete_notification",
)
