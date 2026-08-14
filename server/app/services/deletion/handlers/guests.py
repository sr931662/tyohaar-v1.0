"""
Guest personal data — third parties who never signed up.

`invitation_guests` and `celebration_guests` hold the name, phone and email of
people who were invited to something. They never created a Tyohaar account and
never met a Tyohaar consent flow, so their data does not belong to the host and
must not silently inherit the host's lifetime.

Two rules operate here, and they compose rather than override:

1. **Host deletion** removes guests attached to that host's celebrations and
   invitations. This is an explicit handler and deliberately does *not* lean on
   the `celebrations → celebration_guests` CASCADE, because booked celebrations
   are never deleted (they are sanitised in place) and so nothing would cascade.

2. **Event expiry** removes guest contact details a configurable period after
   the event they belong to, regardless of account state. Run by the daily job,
   independent of any deletion request.

Whichever comes first wins. A host who deletes the month after their wedding
takes the guest list with them; a host who never deletes still loses it once
the event window passes.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.retention import GUEST_PII_AFTER_EVENT_DAYS
from app.models.invitations.invitation import Invitation
from app.models.invitations.invitation_guest import InvitationGuest
from app.models.occasions.celebration import Celebration
from app.models.occasions.celebration_guest import CelebrationGuest
from app.models.occasions.celebration_guest_history import CelebrationGuestHistory
from app.services.deletion.registry import (
    TIER_LEAF,
    PurgeReport,
    register_purge,
)


@register_purge("guests", order=TIER_LEAF - 10)
async def purge_guests(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Guest rows belonging to this host's celebrations and invitations."""
    report = PurgeReport(handler="guests")

    celebration_ids = list(
        (
            await session.execute(
                select(Celebration.id).where(Celebration.customer_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    invitation_ids = list(
        (
            await session.execute(
                select(Invitation.id).where(Invitation.owner_id == user_id)
            )
        )
        .scalars()
        .all()
    )

    if celebration_ids:
        # History rows reference the guest — clear them first.
        result = await session.execute(
            delete(CelebrationGuestHistory).where(
                CelebrationGuestHistory.celebration_id.in_(celebration_ids)
            )
        )
        report.count("celebration_guest_history", result.rowcount or 0)

        result = await session.execute(
            delete(CelebrationGuest).where(
                CelebrationGuest.celebration_id.in_(celebration_ids)
            )
        )
        report.count("celebration_guests", result.rowcount or 0)

    if invitation_ids:
        result = await session.execute(
            delete(InvitationGuest).where(
                InvitationGuest.invitation_id.in_(invitation_ids)
            )
        )
        report.count("invitation_guests", result.rowcount or 0)

    # The deleting user may themselves appear as a guest on someone else's
    # celebration. Sever that link without touching the host's guest list —
    # the row stays (it is the host's record of who came) but stops pointing
    # at a person we have deleted.
    result = await session.execute(
        update(CelebrationGuest)
        .where(CelebrationGuest.user_id == user_id)
        .values(user_id=None)
    )
    report.count("guest_backreferences_cleared", result.rowcount or 0)

    return report


async def purge_expired_guest_pii(
    session: AsyncSession,
    *,
    today: date | None = None,
    batch_size: int = 500,
) -> dict[str, int]:
    """Delete guest contact data for events that ended long enough ago.

    Independent of accounts entirely: the clock runs from the event date, so
    a host who is still an active user also loses stale guest lists. Batched
    and idempotent — safe to run every day, and re-running finds nothing.

    Returns per-table counts for the job's report.
    """
    today = today or date.today()
    cutoff = today - timedelta(days=GUEST_PII_AFTER_EVENT_DAYS)
    counts: dict[str, int] = {}

    expired_celebrations = list(
        (
            await session.execute(
                select(Celebration.id)
                .where(Celebration.celebration_date < cutoff)
                .limit(batch_size)
            )
        )
        .scalars()
        .all()
    )
    if expired_celebrations:
        result = await session.execute(
            delete(CelebrationGuestHistory).where(
                CelebrationGuestHistory.celebration_id.in_(expired_celebrations)
            )
        )
        counts["celebration_guest_history"] = result.rowcount or 0

        result = await session.execute(
            delete(CelebrationGuest).where(
                CelebrationGuest.celebration_id.in_(expired_celebrations)
            )
        )
        counts["celebration_guests"] = result.rowcount or 0

    expired_invitations = list(
        (
            await session.execute(
                select(Invitation.id)
                .where(Invitation.event_date < cutoff)
                .limit(batch_size)
            )
        )
        .scalars()
        .all()
    )
    if expired_invitations:
        result = await session.execute(
            delete(InvitationGuest).where(
                InvitationGuest.invitation_id.in_(expired_invitations)
            )
        )
        counts["invitation_guests"] = result.rowcount or 0

    return counts
