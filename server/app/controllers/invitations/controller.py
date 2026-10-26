"""
Invitations Controller — guest invitations, public guest pages, gate entry,
delegated gate access and the admin view.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends, Header, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from app.core.config import settings
from app.core.current_user import CurrentUserDep
from app.core.dependencies import InvitationServiceDep
from app.core.pagination import OffsetPaginationParams, get_offset_pagination
from app.core.permissions import AdminDep, StaffDep, SuperAdminDep
from app.core.responses import PaginatedMeta, PaginatedResponse, SuccessResponse
from app.models.enums import (
    GuestEntryAction,
    GuestEntryStatus,
    GuestPassStatus,
    GuestVerificationResult,
    RSVPStatus,
)
from app.schemas.invitations import (
    AdminInvitationDetail,
    AdminInvitationRow,
    BulkCreateResult,
    DeliveryCapabilities,
    EmailSendResult,
    EntryLogItem,
    GateAccessCreate,
    GateAccessResponse,
    GateCheckIn,
    GateGuest,
    GateRequest,
    GateResult,
    GateSession,
    GuestInvitationBulkCreate,
    GuestInvitationCreate,
    GuestInvitationDetail,
    GuestInvitationResponse,
    GuestInvitationRevoke,
    GuestInvitationShared,
    GuestInvitationUpdate,
    InvitationSummary,
    PublicInvitation,
    PublicRSVPSubmit,
)
from app.services.invitations import pages
from app.services.invitations.rules import InvitationPolicy
from app.services.invitations.service import GateScope, InvitationService


def public_base_url(request: Request) -> str:
    """Origin for shareable links: configured, else what the client reached."""
    if settings.PUBLIC_BASE_URL:
        return settings.PUBLIC_BASE_URL.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc)).split(",")[0].strip()
    return f"{proto}://{host}"


def _page(items: list, total: int, page: int, page_size: int) -> PaginatedResponse:
    pages_ = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        data=items,
        meta=PaginatedMeta(
            page=page, page_size=page_size, total=total, total_pages=pages_,
            has_next=page < pages_, has_prev=page > 1,
        ),
    )


Pagination = Annotated[OffsetPaginationParams, Depends(get_offset_pagination)]


# ── Host: invitations ─────────────────────────────────────────────────────────

async def list_invitations(
    celebration_id: uuid.UUID,
    request: Request,
    current_user: CurrentUserDep,
    service: InvitationServiceDep,
    pagination: Pagination,
    status_filter: Annotated[str, Query(alias="status")] = "all",
    q: Annotated[str | None, Query(max_length=100)] = None,
    sort: str = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> PaginatedResponse[GuestInvitationResponse]:
    items, total = await service.list_invitations(
        celebration_id, current_user.id, status=status_filter, q=q, sort=sort, order=order,
        page=pagination.page, page_size=pagination.page_size, base_url=public_base_url(request),
    )
    return _page(items, total, pagination.page, pagination.page_size)


async def invitation_summary(
    celebration_id: uuid.UUID, current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[InvitationSummary]:
    return SuccessResponse(data=await service.summary(celebration_id, current_user.id), message="Summary retrieved.")


async def delivery_capabilities(_user: CurrentUserDep) -> SuccessResponse[DeliveryCapabilities]:
    return SuccessResponse(data=InvitationService.delivery_capabilities(), message="Capabilities retrieved.")


async def create_invitation(
    celebration_id: uuid.UUID,
    body: GuestInvitationCreate,
    request: Request,
    response: Response,
    current_user: CurrentUserDep,
    service: InvitationServiceDep,
) -> SuccessResponse[GuestInvitationResponse]:
    result, created = await service.create_invitation(
        celebration_id, current_user, body, base_url=public_base_url(request)
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return SuccessResponse(
        data=result, message="Invitation created." if created else "Invitation already created."
    )


async def bulk_create_invitations(
    celebration_id: uuid.UUID,
    body: GuestInvitationBulkCreate,
    request: Request,
    current_user: CurrentUserDep,
    service: InvitationServiceDep,
) -> SuccessResponse[BulkCreateResult]:
    result = await service.bulk_create(celebration_id, current_user, body, base_url=public_base_url(request))
    return SuccessResponse(data=result, message=f"{result.created} invitation(s) created.")


async def get_invitation(
    celebration_id: uuid.UUID, guest_id: uuid.UUID, request: Request,
    current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[GuestInvitationDetail]:
    result = await service.get_detail(celebration_id, guest_id, current_user.id, base_url=public_base_url(request))
    return SuccessResponse(data=result, message="Invitation retrieved.")


async def update_invitation(
    celebration_id: uuid.UUID, guest_id: uuid.UUID, body: GuestInvitationUpdate, request: Request,
    current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[GuestInvitationResponse]:
    result = await service.update_invitation(celebration_id, guest_id, current_user, body, base_url=public_base_url(request))
    return SuccessResponse(data=result, message="Invitation updated.")


async def revoke_invitation(
    celebration_id: uuid.UUID, guest_id: uuid.UUID, body: GuestInvitationRevoke, request: Request,
    current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[GuestInvitationResponse]:
    result = await service.revoke(celebration_id, guest_id, current_user, body.reason, base_url=public_base_url(request))
    return SuccessResponse(data=result, message="Invitation cancelled.")


async def rotate_invitation(
    celebration_id: uuid.UUID, guest_id: uuid.UUID, request: Request,
    current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[GuestInvitationResponse]:
    result = await service.rotate_credentials(celebration_id, guest_id, current_user, base_url=public_base_url(request))
    return SuccessResponse(data=result, message="New link and pass issued. The old ones no longer work.")


async def mark_invitation_shared(
    celebration_id: uuid.UUID, guest_id: uuid.UUID, body: GuestInvitationShared, request: Request,
    current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[GuestInvitationResponse]:
    result = await service.mark_shared(celebration_id, guest_id, current_user, body.channel, base_url=public_base_url(request))
    return SuccessResponse(data=result, message="Share recorded.")


async def email_invitation(
    celebration_id: uuid.UUID, guest_id: uuid.UUID, request: Request,
    current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[EmailSendResult]:
    result = await service.send_email(celebration_id, guest_id, current_user, base_url=public_base_url(request))
    return SuccessResponse(data=result, message=result.message)


# ── Host: gate ────────────────────────────────────────────────────────────────

async def _host_scope(celebration_id: uuid.UUID, current_user: CurrentUserDep, service: InvitationServiceDep) -> GateScope:
    return await service.host_scope(celebration_id, current_user)

HostScope = Annotated[GateScope, Depends(_host_scope)]


async def host_gate_session(scope: HostScope, service: InvitationServiceDep) -> SuccessResponse[GateSession]:
    return SuccessResponse(data=await service.gate_session(scope), message="Gate session.")


async def host_gate_verify(body: GateRequest, scope: HostScope, service: InvitationServiceDep) -> SuccessResponse[GateResult]:
    result = await service.gate_action(scope, body, GuestEntryAction.VERIFY)
    return SuccessResponse(data=result, message=result.message)


async def host_gate_check_in(body: GateCheckIn, scope: HostScope, service: InvitationServiceDep) -> SuccessResponse[GateResult]:
    result = await service.gate_action(scope, body, GuestEntryAction.CHECK_IN)
    return SuccessResponse(data=result, message=result.message)


async def host_gate_check_out(body: GateRequest, scope: HostScope, service: InvitationServiceDep) -> SuccessResponse[GateResult]:
    result = await service.gate_action(scope, body, GuestEntryAction.CHECK_OUT)
    return SuccessResponse(data=result, message=result.message)


async def host_gate_search(
    scope: HostScope, service: InvitationServiceDep, q: Annotated[str, Query(max_length=60)] = "",
) -> SuccessResponse[list[GateGuest]]:
    return SuccessResponse(data=await service.gate_search(scope, q), message="Search results.")


# ── Host: gate access ─────────────────────────────────────────────────────────

async def list_gate_accesses(
    celebration_id: uuid.UUID, current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[list[GateAccessResponse]]:
    return SuccessResponse(data=await service.list_gate_accesses(celebration_id, current_user.id), message="Gate access retrieved.")


async def create_gate_access(
    celebration_id: uuid.UUID, body: GateAccessCreate, request: Request,
    current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[GateAccessResponse]:
    result = await service.create_gate_access(celebration_id, current_user.id, body, base_url=public_base_url(request))
    return SuccessResponse(data=result, message="Gate access created. Share the link with your entry staff — it is shown only once.")


async def revoke_gate_access(
    celebration_id: uuid.UUID, access_id: uuid.UUID, current_user: CurrentUserDep, service: InvitationServiceDep,
) -> SuccessResponse[GateAccessResponse]:
    result = await service.revoke_gate_access(celebration_id, access_id, current_user.id)
    return SuccessResponse(data=result, message="Gate access revoked.")


# ── Guest (public) ────────────────────────────────────────────────────────────

InviteToken = Annotated[str | None, Header(alias="X-Invite-Token", max_length=128)]


async def invite_page() -> HTMLResponse:
    return pages.invite_page()


async def legacy_rsvp_page(token: str) -> RedirectResponse:
    """Links shared before guest passes pointed here; keep them working."""
    return RedirectResponse(
        f"{settings.API_V1_PREFIX}/public/invite/page#{token}", status_code=status.HTTP_302_FOUND,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )


async def public_invitation(service: InvitationServiceDep, token: InviteToken = None) -> SuccessResponse[PublicInvitation]:
    return SuccessResponse(data=await service.public_view(token), message="Invitation retrieved.")


async def public_rsvp(body: PublicRSVPSubmit, service: InvitationServiceDep, token: InviteToken = None) -> SuccessResponse[PublicInvitation]:
    return SuccessResponse(data=await service.public_rsvp(token, body), message="RSVP recorded.")


# ── Gate (public, delegated access) ───────────────────────────────────────────

async def _gate_scope(
    service: InvitationServiceDep,
    token: Annotated[str | None, Header(alias="X-Gate-Token", max_length=128)] = None,
) -> GateScope:
    return await service.gate_access_scope(token)

GateTokenScope = Annotated[GateScope, Depends(_gate_scope)]


async def gate_page() -> HTMLResponse:
    return pages.gate_page()


async def gate_session(scope: GateTokenScope, service: InvitationServiceDep) -> SuccessResponse[GateSession]:
    return SuccessResponse(data=await service.gate_session(scope), message="Gate session.")


async def gate_verify(body: GateRequest, scope: GateTokenScope, service: InvitationServiceDep) -> SuccessResponse[GateResult]:
    result = await service.gate_action(scope, body, GuestEntryAction.VERIFY)
    return SuccessResponse(data=result, message=result.message)


async def gate_check_in(body: GateCheckIn, scope: GateTokenScope, service: InvitationServiceDep) -> SuccessResponse[GateResult]:
    result = await service.gate_action(scope, body, GuestEntryAction.CHECK_IN)
    return SuccessResponse(data=result, message=result.message)


async def gate_check_out(body: GateRequest, scope: GateTokenScope, service: InvitationServiceDep) -> SuccessResponse[GateResult]:
    result = await service.gate_action(scope, body, GuestEntryAction.CHECK_OUT)
    return SuccessResponse(data=result, message=result.message)


async def gate_search(
    scope: GateTokenScope, service: InvitationServiceDep, q: Annotated[str, Query(max_length=60)] = "",
) -> SuccessResponse[list[GateGuest]]:
    return SuccessResponse(data=await service.gate_search(scope, q), message="Search results.")


# ── Admin ─────────────────────────────────────────────────────────────────────

def _admin_filters(
    q: Annotated[str | None, Query(max_length=100)] = None,
    celebration_id: uuid.UUID | None = None,
    pass_status: GuestPassStatus | None = None,
    entry_status: GuestEntryStatus | None = None,
    rsvp_status: RSVPStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    return {
        "q": q, "celebration_id": celebration_id, "pass_status": pass_status, "entry_status": entry_status,
        "rsvp_status": rsvp_status, "date_from": date_from, "date_to": date_to,
    }

AdminFilters = Annotated[dict, Depends(_admin_filters)]


async def admin_list_invitations(
    staff: StaffDep,
    service: InvitationServiceDep,
    pagination: Pagination,
    filters: AdminFilters,
    sort: str = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> PaginatedResponse[AdminInvitationRow]:
    items, total, page, page_size = await service.admin_list(
        staff, page=pagination.page, page_size=pagination.page_size, sort=sort, order=order, **filters
    )
    return _page(items, total, page, page_size)


async def admin_export_invitations(admin: AdminDep, service: InvitationServiceDep, filters: AdminFilters) -> StreamingResponse:
    rows = await service.admin_export_rows(admin, **filters)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Celebration", "Celebration date", "Celebration status", "Guest", "Phone", "Email",
        "Allowed +", "Pass", "Pass state", "RSVP", "Entry", "Checked in at", "Revoked at", "Invited at",
    ])

    def cell(value) -> str:
        text = "" if value is None else str(getattr(value, "value", value))
        # Neutralise spreadsheet formula injection from guest-entered names.
        return "'" + text if text[:1] in ("=", "+", "-", "@") else text

    for r in rows:
        writer.writerow([cell(v) for v in (
            r.celebration_title, r.celebration_date, r.celebration_status, r.name, r.phone, r.email,
            r.plus_ones_allowed, r.pass_status, r.pass_state, r.rsvp_status, r.entry_status,
            r.checked_in_at, r.revoked_at, r.created_at,
        )])
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=invitations-{date.today().isoformat()}.csv"},
    )


async def admin_get_invitation(guest_id: uuid.UUID, staff: StaffDep, service: InvitationServiceDep) -> SuccessResponse[AdminInvitationDetail]:
    return SuccessResponse(data=await service.admin_detail(staff, guest_id), message="Invitation retrieved.")


async def admin_revoke_invitation(
    guest_id: uuid.UUID, body: GuestInvitationRevoke, admin: AdminDep, service: InvitationServiceDep,
) -> SuccessResponse[AdminInvitationDetail]:
    return SuccessResponse(data=await service.admin_revoke(admin, guest_id, body.reason), message="Invitation revoked.")


async def admin_celebration_summary(
    celebration_id: uuid.UUID, _staff: StaffDep, service: InvitationServiceDep,
) -> SuccessResponse[InvitationSummary]:
    return SuccessResponse(data=await service.admin_summary(celebration_id), message="Summary retrieved.")


async def admin_entry_logs(
    _staff: StaffDep,
    service: InvitationServiceDep,
    pagination: Pagination,
    celebration_id: uuid.UUID | None = None,
    result: GuestVerificationResult | None = None,
    action: GuestEntryAction | None = None,
    failed_only: bool = False,
) -> PaginatedResponse[EntryLogItem]:
    items, total, page, page_size = await service.entry_logs(
        celebration_id=celebration_id, result=result, action=action, failed_only=failed_only,
        page=pagination.page, page_size=pagination.page_size,
    )
    return _page(items, total, page, page_size)


async def admin_get_policy(_admin: AdminDep, service: InvitationServiceDep) -> SuccessResponse[InvitationPolicy]:
    return SuccessResponse(data=await service.get_policy(), message="Policy retrieved.")


async def admin_update_policy(
    body: InvitationPolicy, super_admin: SuperAdminDep, service: InvitationServiceDep,
) -> SuccessResponse[InvitationPolicy]:
    return SuccessResponse(data=await service.update_policy(super_admin, body), message="Policy updated.")
