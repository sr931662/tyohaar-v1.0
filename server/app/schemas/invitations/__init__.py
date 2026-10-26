"""
Guest invitation & gate entry schemas.

Three audiences, three shapes — and none of them overlap by accident:

* **Host** (celebration owner): full guest record incl. contact details, the
  shareable link and entry code, history and entry log.
* **Guest** (public, by link token): their own invitation and the event
  basics. No other guests, no host contact details, no internal notes.
* **Gate operator** (host / delegated gate access / admin): the minimum needed
  to admit someone — name, allowance, arrival window, vehicle, status. Phone
  numbers are masked; notes are never included.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.models.enums import (
    EntryOperatorType,
    GuestEntryAction,
    GuestEntryStatus,
    GuestPassStatus,
    GuestVerificationResult,
    RSVPStatus,
)
from app.schemas.base import BaseSchema

ShareChannel = Literal["share_sheet", "whatsapp", "copy_link"]
EntryMethod = Literal["qr", "manual", "search"]


def _strip_or_none(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


# ── Host: create / edit ───────────────────────────────────────────────────────

class GuestInvitationFields(BaseSchema):
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=320)
    plus_ones_allowed: int = Field(default=0, ge=0, le=50)
    arrival_window_start: time | None = None
    arrival_window_end: time | None = None
    vehicle_number: str | None = Field(default=None, max_length=20)
    group_tag: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000, description="Host-only private note.")

    @field_validator("phone", "email", "vehicle_number", "group_tag", "notes", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return _strip_or_none(v) if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def _email_shape(cls, v: str | None) -> str | None:
        if v is not None and ("@" not in v or v.startswith("@") or v.endswith("@") or " " in v):
            raise ValueError("Enter a valid email address.")
        return v.lower() if v else v

    @field_validator("vehicle_number")
    @classmethod
    def _vehicle_upper(cls, v: str | None) -> str | None:
        return v.upper() if v else v

    @model_validator(mode="after")
    def _window_order(self):
        if (self.arrival_window_start is None) != (self.arrival_window_end is None):
            raise ValueError("Give both the start and end of the arrival window, or neither.")
        return self


class GuestInvitationCreate(GuestInvitationFields):
    name: str = Field(min_length=1, max_length=200)
    client_request_id: str | None = Field(
        default=None,
        min_length=8,
        max_length=64,
        description="Idempotency key; a retried request with the same key returns the original invitation.",
    )


class GuestInvitationBulkCreate(BaseSchema):
    client_request_id: str = Field(min_length=8, max_length=48)
    guests: list[GuestInvitationCreate] = Field(min_length=1)


class GuestInvitationUpdate(GuestInvitationFields):
    """PATCH — only fields that are sent are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    plus_ones_allowed: int | None = Field(default=None, ge=0, le=50)  # type: ignore[assignment]


class GuestInvitationRevoke(BaseSchema):
    reason: str | None = Field(default=None, max_length=300)


class GuestInvitationShared(BaseSchema):
    channel: ShareChannel


# ── Host: responses ───────────────────────────────────────────────────────────

class GuestInvitationResponse(BaseSchema):
    id: uuid.UUID
    celebration_id: uuid.UUID
    name: str
    phone: str | None = None
    email: str | None = None
    group_tag: str | None = None
    notes: str | None = None
    plus_ones_allowed: int
    arrival_window_start: time | None = None
    arrival_window_end: time | None = None
    vehicle_number: str | None = None

    pass_status: GuestPassStatus
    pass_state: str = Field(description="Derived: valid | not_yet_valid | expired | revoked | event_cancelled | postponed | checked_in | checked_out | used")
    rsvp_status: RSVPStatus
    rsvp_party_size: int | None = None
    rsvp_responded_at: datetime | None = None
    guest_note: str | None = None
    entry_status: GuestEntryStatus
    checked_in_at: datetime | None = None
    checked_out_at: datetime | None = None
    checked_in_party_size: int | None = None
    invitation_opened_at: datetime | None = None
    last_shared_at: datetime | None = None
    last_shared_channel: str | None = None
    share_count: int = 0
    revoked_at: datetime | None = None
    revoked_reason: str | None = None
    created_at: datetime

    invite_url: str | None = Field(default=None, description="Guest's personal link — share it, don't publish it.")
    entry_code: str | None = Field(default=None, description="Formatted gate code, e.g. K7QM-3XPD.")
    qr_payload: str | None = Field(default=None, description="Exact string to encode in the pass QR.")


class GuestHistoryItem(BaseSchema):
    id: uuid.UUID
    celebration_guest_id: uuid.UUID
    event_type: str
    previous_status: RSVPStatus | None = None
    new_status: RSVPStatus | None = None
    actor_type: str | None = None
    actor_label: str | None = None
    details: dict | None = None
    occurred_at: datetime


class EntryLogItem(BaseSchema):
    id: uuid.UUID
    celebration_id: uuid.UUID
    celebration_guest_id: uuid.UUID | None = None
    guest_name: str | None = None
    action: GuestEntryAction
    result: GuestVerificationResult
    method: str
    party_size: int | None = None
    operator_type: EntryOperatorType
    operator_label: str | None = None
    occurred_at: datetime


class GuestInvitationDetail(BaseSchema):
    invitation: GuestInvitationResponse
    history: list[GuestHistoryItem]
    entries: list[EntryLogItem]


class BulkRowResult(BaseSchema):
    index: int
    status: Literal["created", "existing", "duplicate", "error"]
    message: str | None = None
    invitation: GuestInvitationResponse | None = None


class BulkCreateResult(BaseSchema):
    created: int
    skipped: int
    results: list[BulkRowResult]


class InvitationSummary(BaseSchema):
    celebration_id: uuid.UUID
    total: int
    active: int
    revoked: int
    rsvp_attending: int
    rsvp_maybe: int
    rsvp_declined: int
    rsvp_pending: int
    opened: int
    expected_people: int = Field(description="People expected: attending party sizes (or invitee + allowance when unknown) for active, not-declined passes.")
    arrived_guests: int
    arrived_people: int
    inside_now: int
    checked_out: int
    still_expected: int = Field(description="Active, not-declined invitations whose guest has not arrived yet.")


class DeliveryCapabilities(BaseSchema):
    email: bool = Field(description="True when SMTP is configured on the server.")
    share_sheet: bool = True
    whatsapp: bool = True
    copy_link: bool = True


class EmailSendResult(BaseSchema):
    sent: bool
    message: str


# ── Guest (public) ────────────────────────────────────────────────────────────

class PublicInvitation(BaseSchema):
    guest_name: str
    host_first_name: str | None = None
    celebration_title: str
    celebration_date: date
    start_time: time | None = None
    end_time: time | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    map_url: str | None = None
    theme_colors: dict | None = None
    plus_ones_allowed: int
    arrival_window_start: time | None = None
    arrival_window_end: time | None = None
    rsvp_status: RSVPStatus
    rsvp_party_size: int | None = None
    can_respond: bool
    pass_state: str
    entry_code: str | None = Field(default=None, description="Only while the pass can still be used.")
    qr_svg: str | None = Field(default=None, description="Inline SVG of the pass QR; only while usable.")
    celebration_status: str


class PublicRSVPSubmit(BaseSchema):
    rsvp_status: RSVPStatus
    party_size: int | None = Field(default=None, ge=1, le=51)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("rsvp_status")
    @classmethod
    def _guest_choosable(cls, v: RSVPStatus) -> RSVPStatus:
        if v not in (RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.DECLINED):
            raise ValueError("rsvp_status must be one of: attending, maybe, declined")
        return v


# ── Gate ──────────────────────────────────────────────────────────────────────

class GateRequest(BaseSchema):
    """Identify a pass by its code (scan / typed) or by guest id (from search)."""

    code: str | None = Field(default=None, max_length=40)
    guest_id: uuid.UUID | None = None
    method: EntryMethod = "manual"
    client_scan_id: str | None = Field(default=None, min_length=8, max_length=64)

    @model_validator(mode="after")
    def _one_identifier(self):
        if not self.code and not self.guest_id:
            raise ValueError("Provide the entry code or a guest from search.")
        return self


class GateCheckIn(GateRequest):
    party_size: int = Field(default=1, ge=1, le=51)


class GateGuest(BaseSchema):
    id: uuid.UUID
    name: str
    phone_masked: str | None = None
    plus_ones_allowed: int
    rsvp_status: RSVPStatus
    rsvp_party_size: int | None = None
    entry_status: GuestEntryStatus
    checked_in_at: datetime | None = None
    checked_in_party_size: int | None = None
    arrival_window_start: time | None = None
    arrival_window_end: time | None = None
    vehicle_number: str | None = None


class GateResult(BaseSchema):
    result: GuestVerificationResult
    message: str
    recorded: bool = Field(description="True only when the server persisted an entry or exit.")
    replayed: bool = Field(default=False, description="True when this repeats an earlier identical scan.")
    warnings: list[str] = []
    guest: GateGuest | None = None
    celebration_title: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    occurred_at: datetime | None = None


class GateSession(BaseSchema):
    celebration_id: uuid.UUID
    celebration_title: str
    celebration_date: date
    start_time: time | None = None
    end_time: time | None = None
    venue_name: str | None = None
    operator_label: str
    expires_at: datetime | None = None
    arrived_guests: int
    arrived_people: int
    still_expected: int


class GateAccessCreate(BaseSchema):
    label: str = Field(min_length=2, max_length=120)
    valid_hours: int | None = Field(default=None, ge=1, le=24 * 14)


class GateAccessResponse(BaseSchema):
    id: uuid.UUID
    celebration_id: uuid.UUID
    label: str
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime
    is_active: bool
    console_url: str | None = Field(default=None, description="Returned once, at creation only.")


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminInvitationRow(BaseSchema):
    id: uuid.UUID
    celebration_id: uuid.UUID
    celebration_title: str
    celebration_date: date
    celebration_status: str
    host_id: uuid.UUID
    name: str
    phone: str | None = None
    email: str | None = None
    plus_ones_allowed: int
    pass_status: GuestPassStatus
    pass_state: str
    rsvp_status: RSVPStatus
    entry_status: GuestEntryStatus
    checked_in_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class AdminInvitationDetail(BaseSchema):
    invitation: AdminInvitationRow
    revoked_reason: str | None = None
    history: list[GuestHistoryItem]
    entries: list[EntryLogItem]
