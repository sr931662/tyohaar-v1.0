"""
Events Controller — invitation management for organisers, and the public guest
invitation (page, JSON, RSVP, calendar).
"""

from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import Depends, File, Header, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.controllers.invitations.controller import Pagination, _page, public_base_url
from app.core.current_user import CurrentUserDep
from app.core.dependencies import EventServiceDep
from app.core.permissions import CurrentVendorIdDep
from app.core.responses import PaginatedResponse, SuccessResponse
from app.schemas.events import (
    ActivityItem,
    EventAnalytics,
    EventCreate,
    EventDetail,
    EventList,
    EventUpdate,
    FoodSummary,
    FunctionCreate,
    FunctionReorder,
    FunctionResponse,
    FunctionUpdate,
    GeneralLinkUpdate,
    GuestFunctionsUpdate,
    GuestGroupCreate,
    GuestGroupResponse,
    GuestGroupUpdate,
    ImportResult,
    InvitationSettingsUpdate,
    OperationsApproval,
    PreviewLink,
    PublicActivity,
    PublicClaim,
    PublicClaimResult,
    PublicInvitationPage,
    PublicRSVPRequest,
    ReminderCandidates,
    ReminderRecord,
    RSVPRow,
    VendorGuestSummary,
)
from app.services.exceptions import ValidationError
from app.services.invitations import guest_page
from app.services.occasions.exceptions import GuestNotFoundError

# Link-preview fetchers and automated clients. Over-matching only means one
# visit isn't counted; under-matching means reporting a crawler as a guest, so
# anything self-described as automated is treated as not a person.
_AUTOMATED_AGENT = re.compile(
    r"whatsapp|facebookexternalhit|facebot|meta-external|telegrambot|twitterbot|slackbot|linkedinbot|"
    r"discordbot|skypeuripreview|googlebot|bingbot|applebot|pinterest|embedly|preview|"
    r"crawler|spider|\bbot\b|bot/|headless|curl|wget|python-|httpx|axios|okhttp|go-http|java/|libwww",
    re.IGNORECASE,
)


def is_real_browser(user_agent: str | None) -> bool:
    return bool(user_agent) and not _AUTOMATED_AGENT.search(user_agent)


def api_origin(request: Request) -> str:
    """Where the page's script should call; differs from the page origin behind the website proxy."""
    return public_base_url(request)


# ── Organiser: events ─────────────────────────────────────────────────────────

async def list_events(current_user: CurrentUserDep, service: EventServiceDep) -> SuccessResponse[EventList]:
    return SuccessResponse(data=await service.list_events(current_user.id), message="Events retrieved.")


async def create_event(
    body: EventCreate, request: Request, response: Response, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[EventDetail]:
    event, created = await service.create_event(current_user, body, base_url=public_base_url(request))
    if not created:
        response.status_code = status.HTTP_200_OK
    return SuccessResponse(data=event, message="Event created." if created else "Event already created.")


async def get_event(
    celebration_id: uuid.UUID, request: Request, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[EventDetail]:
    return SuccessResponse(
        data=await service.get_event(celebration_id, current_user.id, base_url=public_base_url(request)),
        message="Event retrieved.",
    )


async def update_event(
    celebration_id: uuid.UUID, body: EventUpdate, request: Request, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[EventDetail]:
    return SuccessResponse(
        data=await service.update_event(celebration_id, current_user.id, body, base_url=public_base_url(request)),
        message="Event updated.",
    )


async def update_invitation_settings(
    celebration_id: uuid.UUID, body: InvitationSettingsUpdate, request: Request,
    current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[EventDetail]:
    return SuccessResponse(
        data=await service.update_settings(celebration_id, current_user.id, body, base_url=public_base_url(request)),
        message="Invitation updated.",
    )


async def publish_invitation(
    celebration_id: uuid.UUID, request: Request, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[EventDetail]:
    return SuccessResponse(
        data=await service.publish(celebration_id, current_user.id, base_url=public_base_url(request)),
        message="Invitation published.",
    )


async def unpublish_invitation(
    celebration_id: uuid.UUID, request: Request, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[EventDetail]:
    return SuccessResponse(
        data=await service.publish(celebration_id, current_user.id, base_url=public_base_url(request), published=False),
        message="Invitation unpublished.",
    )


async def update_general_link(
    celebration_id: uuid.UUID, body: GeneralLinkUpdate, request: Request,
    current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[EventDetail]:
    return SuccessResponse(
        data=await service.update_general_link(celebration_id, current_user.id, body, base_url=public_base_url(request)),
        message="General link updated.",
    )


async def invitation_preview_link(
    celebration_id: uuid.UUID, request: Request, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[PreviewLink]:
    return SuccessResponse(
        data=await service.preview_link(celebration_id, current_user.id, base_url=public_base_url(request)),
        message="Preview link created.",
    )


# ── Organiser: functions ──────────────────────────────────────────────────────

async def create_function(
    celebration_id: uuid.UUID, body: FunctionCreate, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[FunctionResponse]:
    return SuccessResponse(data=await service.create_function(celebration_id, current_user.id, body), message="Function added.")


async def reorder_functions(
    celebration_id: uuid.UUID, body: FunctionReorder, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[list[FunctionResponse]]:
    return SuccessResponse(
        data=await service.reorder_functions(celebration_id, current_user.id, body.function_ids),
        message="Functions reordered.",
    )


async def update_function(
    celebration_id: uuid.UUID, function_id: uuid.UUID, body: FunctionUpdate,
    current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[FunctionResponse]:
    return SuccessResponse(
        data=await service.update_function(celebration_id, function_id, current_user.id, body),
        message="Function updated.",
    )


async def delete_function(
    celebration_id: uuid.UUID, function_id: uuid.UUID, current_user: CurrentUserDep, service: EventServiceDep,
) -> None:
    await service.delete_function(celebration_id, function_id, current_user.id)


async def set_guest_functions(
    celebration_id: uuid.UUID, body: GuestFunctionsUpdate, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[int]:
    return SuccessResponse(data=await service.set_guest_functions(celebration_id, current_user, body), message="Guests updated.")


# ── Organiser: households, import ─────────────────────────────────────────────

async def create_group(
    celebration_id: uuid.UUID, body: GuestGroupCreate, request: Request,
    current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[list[GuestGroupResponse]]:
    return SuccessResponse(
        data=await service.create_group(celebration_id, current_user.id, body, base_url=public_base_url(request)),
        message="Household added.",
    )


async def update_group(
    celebration_id: uuid.UUID, group_id: uuid.UUID, body: GuestGroupUpdate, request: Request,
    current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[list[GuestGroupResponse]]:
    return SuccessResponse(
        data=await service.update_group(celebration_id, group_id, current_user.id, body, base_url=public_base_url(request)),
        message="Household updated.",
    )


async def delete_group(
    celebration_id: uuid.UUID, group_id: uuid.UUID, current_user: CurrentUserDep, service: EventServiceDep,
) -> None:
    await service.delete_group(celebration_id, group_id, current_user.id)


async def import_guests(
    celebration_id: uuid.UUID, request: Request, current_user: CurrentUserDep, service: EventServiceDep,
    file: Annotated[UploadFile, File()],
) -> SuccessResponse[ImportResult]:
    content = await file.read(2 * 1024 * 1024 + 1)
    return SuccessResponse(
        data=await service.import_guests(
            celebration_id, current_user, file.filename or "", content, base_url=public_base_url(request),
        ),
        message="Import finished.",
    )


# ── Organiser: insight ────────────────────────────────────────────────────────

async def event_analytics(
    celebration_id: uuid.UUID, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[EventAnalytics]:
    return SuccessResponse(data=await service.analytics(celebration_id, current_user.id), message="Analytics retrieved.")


async def list_rsvps(
    celebration_id: uuid.UUID, current_user: CurrentUserDep, service: EventServiceDep, pagination: Pagination,
    function_id: uuid.UUID | None = None, status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> PaginatedResponse[RSVPRow]:
    items, total = await service.list_rsvps(
        celebration_id, current_user.id, function_id=function_id, status=status_filter,
        page=pagination.page, page_size=pagination.page_size,
    )
    return _page(items, total, pagination.page, pagination.page_size)


async def food_summary(
    celebration_id: uuid.UUID, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[FoodSummary]:
    return SuccessResponse(data=await service.food_summary(celebration_id, current_user.id), message="Food summary retrieved.")


async def food_report(celebration_id: uuid.UUID, current_user: CurrentUserDep, service: EventServiceDep) -> Response:
    filename, body = await service.food_report_csv(celebration_id, current_user.id)
    return Response(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def event_activity(
    celebration_id: uuid.UUID, current_user: CurrentUserDep, service: EventServiceDep, pagination: Pagination,
) -> PaginatedResponse[ActivityItem]:
    items, total = await service.activity(
        celebration_id, current_user.id, page=pagination.page, page_size=pagination.page_size,
    )
    return _page(items, total, pagination.page, pagination.page_size)


async def reminder_candidates(
    celebration_id: uuid.UUID, request: Request, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[ReminderCandidates]:
    return SuccessResponse(
        data=await service.reminder_candidates(celebration_id, current_user.id, base_url=public_base_url(request)),
        message="Reminder candidates retrieved.",
    )


async def record_reminders(
    celebration_id: uuid.UUID, body: ReminderRecord, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[int]:
    return SuccessResponse(data=await service.record_reminders(celebration_id, current_user, body), message="Reminders recorded.")


async def approve_operations_summary(
    celebration_id: uuid.UUID, body: OperationsApproval, current_user: CurrentUserDep, service: EventServiceDep,
) -> SuccessResponse[FoodSummary]:
    return SuccessResponse(
        data=await service.approve_operations_summary(celebration_id, current_user.id, body),
        message="Summary shared with your vendors.",
    )


async def vendor_guest_summary(
    booking_id: uuid.UUID, vendor_id: CurrentVendorIdDep, service: EventServiceDep,
) -> SuccessResponse[VendorGuestSummary | None]:
    return SuccessResponse(data=await service.vendor_guest_summary(booking_id, vendor_id), message="Guest summary retrieved.")


# ── Guest: the page ───────────────────────────────────────────────────────────

def _problem_page(title: str, text: str, code: int) -> HTMLResponse:
    response = guest_page.problem_page(title, text)
    response.status_code = code
    return response


async def guest_invitation_page(
    token: str, request: Request, service: EventServiceDep, user_agent: Annotated[str | None, Header()] = None,
) -> HTMLResponse:
    """
    The link in the WhatsApp message. Server-rendered, because the crawler that
    builds the preview reads this response and runs no script.
    """
    try:
        meta = await service.resolve_token(token, is_real_browser=is_real_browser(user_agent))
    except GuestNotFoundError:
        return _problem_page(
            "Invitation not found",
            "This link isn't valid. It may have been replaced by a newer one, so please ask your host to send it again.",
            status.HTTP_404_NOT_FOUND,
        )
    if meta["kind"] == "revoked":
        return _problem_page("Invitation cancelled", "The host has cancelled this invitation.", status.HTTP_410_GONE)
    if meta["draft"]:
        return _problem_page(
            "Not published yet", "The host is still preparing this invitation. Please check back soon.",
            status.HTTP_200_OK,
        )
    return guest_page.invitation_page(meta, page_url=_absolute_page_url(request, token), api_origin=api_origin(request), token=token)


def _absolute_page_url(request: Request, token: str) -> str:
    from app.services.invitations.service import InvitationService

    return InvitationService.invite_url(public_base_url(request), token) or ""


async def guest_preview_page(token: str, request: Request, service: EventServiceDep) -> HTMLResponse:
    try:
        meta = await service.preview_meta(token)
    except GuestNotFoundError:
        return _problem_page(
            "Preview expired", "Preview links last 30 minutes. Open the preview again from the app.",
            status.HTTP_404_NOT_FOUND,
        )
    return guest_page.invitation_page(meta, page_url="", api_origin=api_origin(request), token=token)


async def guest_calendar(token: str, service: EventServiceDep) -> PlainTextResponse:
    try:
        filename, body = await service.calendar(token)
    except GuestNotFoundError:
        return PlainTextResponse("Invitation not found.", status_code=status.HTTP_404_NOT_FOUND)
    return PlainTextResponse(
        body, media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


# ── Guest: the page's API ─────────────────────────────────────────────────────

InviteToken = Annotated[str | None, Header(alias="X-Invite-Token")]


async def guest_view(
    service: EventServiceDep, token: InviteToken = None, user_agent: Annotated[str | None, Header()] = None,
) -> SuccessResponse[PublicInvitationPage]:
    return SuccessResponse(
        data=await service.public_view(token, is_real_browser=is_real_browser(user_agent)),
        message="Invitation retrieved.",
    )


async def guest_preview(service: EventServiceDep, token: InviteToken = None) -> SuccessResponse[PublicInvitationPage]:
    if not token:
        raise ValidationError("Preview link is incomplete.")
    return SuccessResponse(data=await service.preview_page(token), message="Preview retrieved.")


async def guest_activity(body: PublicActivity, service: EventServiceDep, token: InviteToken = None) -> Response:
    if body.type == "rsvp_started":
        await service.track_rsvp_started(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def guest_rsvp(
    body: PublicRSVPRequest, service: EventServiceDep, token: InviteToken = None,
) -> SuccessResponse[PublicInvitationPage]:
    return SuccessResponse(data=await service.submit_rsvp(token, body), message="Thank you for responding.")


async def guest_claim(
    body: PublicClaim, request: Request, service: EventServiceDep, token: InviteToken = None,
) -> SuccessResponse[PublicClaimResult]:
    return SuccessResponse(
        data=await service.claim_general_link(token, body, base_url=public_base_url(request)),
        message="Welcome.",
    )
