"""
Invitation business rules — pure functions, no I/O.

Everything that decides whether a pass admits someone lives here so the gate
endpoints, the guest page, the host app and the admin panel all agree, and so
the rules can be tested without a database.

State model (three independent axes, never folded into one field):

* ``pass_status``  ACTIVE | REVOKED         — stored; REVOKED is terminal.
* ``rsvp_status``  pending | attending | maybe | declined | no_response
* ``entry_status`` NOT_ARRIVED | CHECKED_IN | CHECKED_OUT

Plus two *derived* conditions computed against the celebration at the moment
of the request, so editing the event moves every pass with it:

* outside the entry window → NOT_YET_VALID / EXPIRED
* celebration CANCELLED → EVENT_CANCELLED; POSTPONED → DENIED

Transitions enforced by the service (and backed by conditional UPDATEs):

    NOT_ARRIVED ──check-in──▶ CHECKED_IN ──check-out──▶ CHECKED_OUT
         ▲                                                  │
         └──────────── check-in only if allow_reentry ──────┘

A declined RSVP does not block entry — people change their minds — but the
gate is shown a warning. Revocation blocks verify/check-in immediately;
check-out is always allowed for someone currently inside.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.models.enums import (
    CelebrationStatus,
    GuestEntryAction,
    GuestEntryStatus,
    GuestPassStatus,
    GuestVerificationResult as R,
    RSVPStatus,
)

POLICY_SETTING_KEY = "invitations.policy"


class InvitationPolicy(BaseModel):
    """
    Platform-wide invitation policy (stored as JSON in app_settings under
    ``invitations.policy``; editable by super-admins only). Missing keys fall
    back to these defaults, so an absent setting is a valid configuration.
    """

    max_plus_ones: int = Field(default=10, ge=0, le=50)
    entry_grace_minutes_before: int = Field(default=120, ge=0, le=24 * 60)
    entry_grace_minutes_after: int = Field(default=180, ge=0, le=24 * 60)
    allow_reentry: bool = False
    max_invite_days_in_advance: int = Field(default=365, ge=1, le=730)
    bulk_create_limit: int = Field(default=100, ge=1, le=500)
    notify_host_on_check_in: bool = True
    gate_access_max_hours: int = Field(default=72, ge=1, le=24 * 14)


# ── Time ──────────────────────────────────────────────────────────────────────

def event_zone(tz_name: str) -> ZoneInfo:
    return ZoneInfo(tz_name)


def event_today(tz_name: str, now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    return now.astimezone(event_zone(tz_name)).date()


def entry_window(
    celebration_date: date,
    start_time: time | None,
    end_time: time | None,
    *,
    tz_name: str,
    policy: InvitationPolicy,
) -> tuple[datetime, datetime]:
    """
    The UTC instants between which a pass admits entry.

    Without a start time the whole event day counts; without an end time the
    day ends at midnight. An end time at or before the start time means the
    event runs past midnight. The policy's grace periods are applied to both
    ends so early and late arrivals are not turned away at the boundary.
    """
    tz = event_zone(tz_name)
    start_local = datetime.combine(celebration_date, start_time or time(0, 0), tzinfo=tz)
    if end_time is None:
        end_local = datetime.combine(celebration_date + timedelta(days=1), time(0, 0), tzinfo=tz)
    else:
        end_local = datetime.combine(celebration_date, end_time, tzinfo=tz)
        if start_time is not None and end_time <= start_time:
            end_local += timedelta(days=1)
    return (
        (start_local - timedelta(minutes=policy.entry_grace_minutes_before)).astimezone(timezone.utc),
        (end_local + timedelta(minutes=policy.entry_grace_minutes_after)).astimezone(timezone.utc),
    )


# ── Evaluation ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Evaluation:
    result: R
    reason: str
    warnings: tuple[str, ...] = ()

    @property
    def admits(self) -> bool:
        return self.result in (R.VALID, R.CHECKED_IN)


MESSAGES: dict[R, str] = {
    R.VALID: "Pass is valid.",
    R.CHECKED_IN: "Entry recorded.",
    R.CHECKED_OUT: "Exit recorded.",
    R.ALREADY_CHECKED_IN: "This guest is already checked in.",
    R.ALREADY_USED: "This pass has already been used and re-entry is not allowed.",
    R.NOT_CHECKED_IN: "This guest has not been checked in.",
    R.INVALID: "No matching invitation for this event.",
    R.EXPIRED: "This pass has expired.",
    R.NOT_YET_VALID: "This pass is not valid yet.",
    R.REVOKED: "This invitation was cancelled by the host.",
    R.EVENT_CANCELLED: "This event has been cancelled.",
    R.DENIED: "Entry is not allowed for this event right now.",
    R.PARTY_SIZE_EXCEEDED: "More people than this pass allows.",
}


def evaluate(
    *,
    action: GuestEntryAction,
    pass_status: GuestPassStatus,
    entry_status: GuestEntryStatus,
    rsvp_status: RSVPStatus,
    plus_ones_allowed: int,
    celebration_status: CelebrationStatus,
    window: tuple[datetime, datetime],
    now: datetime,
    policy: InvitationPolicy,
    party_size: int | None = None,
) -> Evaluation:
    """Decide the outcome of a gate action. Does not mutate anything."""

    def out(result: R, warnings: tuple[str, ...] = ()) -> Evaluation:
        return Evaluation(result, MESSAGES[result], warnings)

    if action is GuestEntryAction.CHECK_OUT:
        # Recording that someone left is always allowed if they are inside —
        # even after revocation or the end of the window.
        if entry_status is GuestEntryStatus.CHECKED_IN:
            return out(R.CHECKED_OUT)
        return out(R.NOT_CHECKED_IN)

    if pass_status is GuestPassStatus.REVOKED:
        return out(R.REVOKED)
    if celebration_status is CelebrationStatus.CANCELLED:
        return out(R.EVENT_CANCELLED)
    if celebration_status is CelebrationStatus.POSTPONED:
        return Evaluation(R.DENIED, "This event has been postponed.")

    start, end = window
    if now < start:
        return out(R.NOT_YET_VALID)
    if now > end:
        return out(R.EXPIRED)

    if entry_status is GuestEntryStatus.CHECKED_IN:
        return out(R.ALREADY_CHECKED_IN)
    if entry_status is GuestEntryStatus.CHECKED_OUT and not policy.allow_reentry:
        return out(R.ALREADY_USED)

    if party_size is not None and not (1 <= party_size <= 1 + plus_ones_allowed):
        return out(R.PARTY_SIZE_EXCEEDED)

    warnings: tuple[str, ...] = ()
    if rsvp_status is RSVPStatus.DECLINED:
        warnings = ("rsvp_declined",)
    if entry_status is GuestEntryStatus.CHECKED_OUT:
        warnings = warnings + ("reentry",)
    return out(R.CHECKED_IN if action is GuestEntryAction.CHECK_IN else R.VALID, warnings)


def pass_state(
    *,
    pass_status: GuestPassStatus,
    entry_status: GuestEntryStatus,
    celebration_status: CelebrationStatus,
    window: tuple[datetime, datetime],
    now: datetime,
    policy: InvitationPolicy,
) -> str:
    """
    One word describing the pass for the guest page and host lists:
    revoked | event_cancelled | postponed | checked_in | used | checked_out |
    expired | not_yet_valid | valid.
    """
    if pass_status is GuestPassStatus.REVOKED:
        return "revoked"
    if celebration_status is CelebrationStatus.CANCELLED:
        return "event_cancelled"
    if celebration_status is CelebrationStatus.POSTPONED:
        return "postponed"
    if entry_status is GuestEntryStatus.CHECKED_IN:
        return "checked_in"
    start, end = window
    if now > end:
        return "used" if entry_status is GuestEntryStatus.CHECKED_OUT else "expired"
    if entry_status is GuestEntryStatus.CHECKED_OUT:
        return "checked_out" if policy.allow_reentry else "used"
    if now < start:
        return "not_yet_valid"
    return "valid"


def can_rsvp(
    *,
    pass_status: GuestPassStatus,
    celebration_status: CelebrationStatus,
    celebration_date: date,
    today: date,
) -> bool:
    """Responses are accepted until the day before the event (existing rule)."""
    if pass_status is GuestPassStatus.REVOKED:
        return False
    if celebration_status in (CelebrationStatus.CANCELLED, CelebrationStatus.COMPLETED):
        return False
    return today < celebration_date


def can_invite_to(
    *,
    celebration_status: CelebrationStatus,
    celebration_date: date,
    today: date,
    policy: InvitationPolicy,
) -> str | None:
    """None if new invitations may be created, else the reason they may not."""
    if celebration_status is CelebrationStatus.CANCELLED:
        return "This celebration has been cancelled."
    if celebration_status is CelebrationStatus.COMPLETED:
        return "This celebration has already taken place."
    if celebration_date < today:
        return "This celebration's date has passed."
    if (celebration_date - today).days > policy.max_invite_days_in_advance:
        return (
            f"Invitations can be created at most {policy.max_invite_days_in_advance} "
            "days before the celebration."
        )
    return None


def normalize_phone(phone: str | None) -> str | None:
    """Strip formatting so '+91 98765-43210' and '+919876543210' compare equal."""
    if not phone:
        return None
    keep = "".join(ch for ch in phone.strip() if ch.isdigit() or ch == "+")
    if keep.count("+") > 1 or ("+" in keep and not keep.startswith("+")):
        keep = keep.replace("+", "")
    digits = keep.lstrip("+")
    return keep if 7 <= len(digits) <= 15 else None


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"••••{digits[-4:]}" if len(digits) >= 4 else "••••"
