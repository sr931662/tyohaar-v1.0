"""
Invitations Routes — guest invitations, guest passes and gate entry.

Four audiences, four route groups:
  * /celebrations/{id}/invitations…, /gate…, /gate-access…  — the host (owner)
  * /public/invite/…                                          — the guest, by link token
  * /public/gate/…                                            — delegated entry staff, by gate token
  * /admin/invitations/…                                      — staff (read) / admins (write)

Static segments are registered before `{guest_id}` routes so they are never
captured as an id.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import HTMLResponse

from app.controllers.invitations import controller as ctrl
from app.core.rate_limit import GATE_RATE_LIMIT, PUBLIC_INVITE_RATE_LIMIT, rate_limit
from app.core.responses import PaginatedResponse, SuccessResponse
from app.schemas.invitations import (
    AdminInvitationDetail,
    AdminInvitationRow,
    BulkCreateResult,
    DeliveryCapabilities,
    EmailSendResult,
    EntryLogItem,
    GateAccessResponse,
    GateGuest,
    GateResult,
    GateSession,
    GuestInvitationDetail,
    GuestInvitationResponse,
    InvitationSummary,
    PublicInvitation,
)
from app.services.invitations.rules import InvitationPolicy

router = APIRouter(tags=["Invitations"])
public_router = APIRouter(tags=["Invitations (public)"])
admin_router = APIRouter(prefix="/admin/invitations", tags=["Invitations (admin)"])

_invite_limit = [Depends(rate_limit(PUBLIC_INVITE_RATE_LIMIT))]
_gate_limit = [Depends(rate_limit(GATE_RATE_LIMIT))]


def _route(r: APIRouter, path: str, endpoint, methods: list[str], model=None, code=status.HTTP_200_OK, summary="", **kw):
    r.add_api_route(
        path, endpoint, methods=methods, response_model=model, status_code=code, summary=summary,
        operation_id=f"invitations_{endpoint.__name__}", **kw,
    )


# ── Host: invitations ─────────────────────────────────────────────────────────

_C = "/celebrations/{celebration_id}"

_route(router, "/invitations/capabilities", ctrl.delivery_capabilities, ["GET"],
       SuccessResponse[DeliveryCapabilities], summary="Delivery channels the server can genuinely provide")
_route(router, f"{_C}/invitations", ctrl.list_invitations, ["GET"],
       PaginatedResponse[GuestInvitationResponse], summary="List guest invitations (filter, search, sort, paginate)")
_route(router, f"{_C}/invitations", ctrl.create_invitation, ["POST"],
       SuccessResponse[GuestInvitationResponse], status.HTTP_201_CREATED,
       summary="Create a guest invitation (idempotent with client_request_id)")
_route(router, f"{_C}/invitations/summary", ctrl.invitation_summary, ["GET"],
       SuccessResponse[InvitationSummary], summary="Invitation, RSVP and arrival counts")
_route(router, f"{_C}/invitations/bulk", ctrl.bulk_create_invitations, ["POST"],
       SuccessResponse[BulkCreateResult], summary="Invite several guests at once; per-row results")
_route(router, f"{_C}/invitations/{{guest_id}}", ctrl.get_invitation, ["GET"],
       SuccessResponse[GuestInvitationDetail], summary="Invitation detail with history and entry log")
_route(router, f"{_C}/invitations/{{guest_id}}", ctrl.update_invitation, ["PATCH"],
       SuccessResponse[GuestInvitationResponse], summary="Edit an invitation")
_route(router, f"{_C}/invitations/{{guest_id}}/revoke", ctrl.revoke_invitation, ["POST"],
       SuccessResponse[GuestInvitationResponse], summary="Cancel an invitation (terminal)")
_route(router, f"{_C}/invitations/{{guest_id}}/rotate", ctrl.rotate_invitation, ["POST"],
       SuccessResponse[GuestInvitationResponse], summary="Issue a new link and pass; old ones stop working")
_route(router, f"{_C}/invitations/{{guest_id}}/shared", ctrl.mark_invitation_shared, ["POST"],
       SuccessResponse[GuestInvitationResponse], summary="Record a share the device confirmed")
_route(router, f"{_C}/invitations/{{guest_id}}/email", ctrl.email_invitation, ["POST"],
       SuccessResponse[EmailSendResult], summary="Email the invitation (only when SMTP is configured)")

# ── Host: gate ────────────────────────────────────────────────────────────────

_route(router, f"{_C}/gate/session", ctrl.host_gate_session, ["GET"], SuccessResponse[GateSession],
       summary="Gate counters for the host's own scanner")
_route(router, f"{_C}/gate/verify", ctrl.host_gate_verify, ["POST"], SuccessResponse[GateResult],
       summary="Verify a pass without recording entry", dependencies=_gate_limit)
_route(router, f"{_C}/gate/check-in", ctrl.host_gate_check_in, ["POST"], SuccessResponse[GateResult],
       summary="Record entry (concurrency-safe, retry-safe)", dependencies=_gate_limit)
_route(router, f"{_C}/gate/check-out", ctrl.host_gate_check_out, ["POST"], SuccessResponse[GateResult],
       summary="Record exit", dependencies=_gate_limit)
_route(router, f"{_C}/gate/search", ctrl.host_gate_search, ["GET"], SuccessResponse[list[GateGuest]],
       summary="Find a guest by name / last phone digits", dependencies=_gate_limit)

# ── Host: gate access ─────────────────────────────────────────────────────────

_route(router, f"{_C}/gate-access", ctrl.list_gate_accesses, ["GET"], SuccessResponse[list[GateAccessResponse]],
       summary="List delegated gate accesses")
_route(router, f"{_C}/gate-access", ctrl.create_gate_access, ["POST"], SuccessResponse[GateAccessResponse],
       status.HTTP_201_CREATED, summary="Issue a gate access link for entry staff (shown once)")
_route(router, f"{_C}/gate-access/{{access_id}}/revoke", ctrl.revoke_gate_access, ["POST"],
       SuccessResponse[GateAccessResponse], summary="Revoke a gate access link")

# ── Guest (public) ────────────────────────────────────────────────────────────

_route(public_router, "/public/invite/page", ctrl.invite_page, ["GET"], None,
       summary="Guest invitation page", response_class=HTMLResponse, include_in_schema=False)
_route(public_router, "/public/invite/view", ctrl.public_invitation, ["GET"], SuccessResponse[PublicInvitation],
       summary="Guest's own invitation (X-Invite-Token)", dependencies=_invite_limit)
_route(public_router, "/public/invite/rsvp", ctrl.public_rsvp, ["POST"], SuccessResponse[PublicInvitation],
       summary="Guest RSVP (X-Invite-Token)", dependencies=_invite_limit)

# ── Gate (public, delegated) ──────────────────────────────────────────────────

_route(public_router, "/public/gate/page", ctrl.gate_page, ["GET"], None,
       summary="Gate console", response_class=HTMLResponse, include_in_schema=False)
_route(public_router, "/public/gate/session", ctrl.gate_session, ["GET"], SuccessResponse[GateSession],
       summary="Gate session (X-Gate-Token)", dependencies=_gate_limit)
_route(public_router, "/public/gate/verify", ctrl.gate_verify, ["POST"], SuccessResponse[GateResult],
       summary="Verify a pass (X-Gate-Token)", dependencies=_gate_limit)
_route(public_router, "/public/gate/check-in", ctrl.gate_check_in, ["POST"], SuccessResponse[GateResult],
       summary="Record entry (X-Gate-Token)", dependencies=_gate_limit)
_route(public_router, "/public/gate/check-out", ctrl.gate_check_out, ["POST"], SuccessResponse[GateResult],
       summary="Record exit (X-Gate-Token)", dependencies=_gate_limit)
_route(public_router, "/public/gate/search", ctrl.gate_search, ["GET"], SuccessResponse[list[GateGuest]],
       summary="Find a guest (X-Gate-Token)", dependencies=_gate_limit)

# ── Admin ─────────────────────────────────────────────────────────────────────

_route(admin_router, "", ctrl.admin_list_invitations, ["GET"], PaginatedResponse[AdminInvitationRow],
       summary="All invitations (staff; contact details masked for support)")
_route(admin_router, "/export.csv", ctrl.admin_export_invitations, ["GET"], None,
       summary="Export filtered invitations as CSV (admin)")
_route(admin_router, "/entry-logs", ctrl.admin_entry_logs, ["GET"], PaginatedResponse[EntryLogItem],
       summary="Check-in activity and failed verification attempts")
_route(admin_router, "/policy", ctrl.admin_get_policy, ["GET"], SuccessResponse[InvitationPolicy],
       summary="Invitation policy (admin)")
_route(admin_router, "/policy", ctrl.admin_update_policy, ["PUT"], SuccessResponse[InvitationPolicy],
       summary="Update invitation policy (super-admin)")
_route(admin_router, "/celebrations/{celebration_id}/summary", ctrl.admin_celebration_summary, ["GET"],
       SuccessResponse[InvitationSummary], summary="Event-level guest counts")
_route(admin_router, "/{guest_id}", ctrl.admin_get_invitation, ["GET"], SuccessResponse[AdminInvitationDetail],
       summary="Invitation detail with audit trail")
_route(admin_router, "/{guest_id}/revoke", ctrl.admin_revoke_invitation, ["POST"],
       SuccessResponse[AdminInvitationDetail], summary="Revoke a compromised or invalid invitation (admin)")
