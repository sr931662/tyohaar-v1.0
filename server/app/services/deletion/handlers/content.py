"""
Tier: user-generated content.

Everything here belongs unambiguously to the account owner and has no legal,
security or counterparty reason to survive. It is deleted outright.

Ordering inside this module matters more than it looks. Several children hold
`RESTRICT` foreign keys onto `celebrations`, so they must be gone before the
celebrations handler runs — expenses and memories in particular. The tier
numbers encode that; do not reorder without re-reading the FK constraints.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budgets.budget import Budget
from app.models.budgets.expense import Expense
from app.models.feedback.feedback import Feedback
from app.models.invitations.invitation import Invitation
from app.models.media.memory import Memory
from app.models.notifications.notification import Notification
from app.models.occasions.celebration import Celebration
from app.models.occasions.celebration_budget import CelebrationBudget
from app.models.occasions.celebration_checklist import CelebrationChecklist
from app.models.occasions.celebration_note import CelebrationNote
from app.models.occasions.celebration_timeline import CelebrationTimeline
from app.models.packages.package_item_like import PackageItemLike
from app.models.packages.package_like import PackageLike
from app.services.deletion.registry import (
    TIER_LEAF,
    TIER_AGGREGATE,
    PurgeReport,
    register_purge,
)


async def _owned_celebration_ids(
    session: AsyncSession, user_id: uuid.UUID
) -> list[uuid.UUID]:
    """Every celebration this user owns, booked or not."""
    result = await session.execute(
        select(Celebration.id).where(Celebration.customer_id == user_id)
    )
    return list(result.scalars().all())


@register_purge("engagement", order=TIER_LEAF)
async def purge_engagement(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Likes and notifications — pure leaf rows, nothing references them."""
    report = PurgeReport(handler="engagement")

    result = await session.execute(
        delete(PackageLike).where(PackageLike.user_id == user_id)
    )
    report.count("package_likes", result.rowcount or 0)

    result = await session.execute(
        delete(PackageItemLike).where(PackageItemLike.user_id == user_id)
    )
    report.count("package_item_likes", result.rowcount or 0)

    # Notifications the user received, and any where they were the sender.
    result = await session.execute(
        delete(Notification).where(Notification.recipient_id == user_id)
    )
    report.count("notifications_received", result.rowcount or 0)

    result = await session.execute(
        delete(Notification).where(Notification.sender_id == user_id)
    )
    report.count("notifications_sent", result.rowcount or 0)

    return report


@register_purge("celebration_children", order=TIER_LEAF + 10)
async def purge_celebration_children(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Checklists, timelines, budgets, notes, memories and expenses.

    These hang off celebrations. They are removed here — before the
    celebrations handler — because expenses and memories hold RESTRICT keys
    that would otherwise block the parent, and because the rest is personal
    planning detail with no reason to survive even on a booked celebration.
    """
    report = PurgeReport(handler="celebration_children")

    celebration_ids = await _owned_celebration_ids(session, user_id)
    if not celebration_ids:
        return report

    # Memories hold RESTRICT on both celebrations and users — they must go
    # before either parent is touched.
    result = await session.execute(
        delete(Memory).where(Memory.customer_id == user_id)
    )
    report.count("memories", result.rowcount or 0)

    # Expenses hold RESTRICT on celebrations and CASCADE on budgets. Delete
    # expenses first, then budgets, then the celebration is unblocked.
    result = await session.execute(
        delete(Expense).where(Expense.celebration_id.in_(celebration_ids))
    )
    report.count("expenses", result.rowcount or 0)

    result = await session.execute(
        delete(Budget).where(Budget.customer_id == user_id)
    )
    report.count("budgets", result.rowcount or 0)

    result = await session.execute(
        delete(CelebrationNote).where(
            CelebrationNote.celebration_id.in_(celebration_ids)
        )
    )
    report.count("celebration_notes", result.rowcount or 0)

    for model, label in (
        (CelebrationChecklist, "celebration_checklists"),
        (CelebrationTimeline, "celebration_timelines"),
        (CelebrationBudget, "celebration_budgets"),
    ):
        result = await session.execute(
            delete(model).where(model.celebration_id.in_(celebration_ids))
        )
        report.count(label, result.rowcount or 0)

    return report


@register_purge("invitations", order=TIER_AGGREGATE)
async def purge_invitations(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Invitations the user sent.

    Guest rows are removed by the dedicated guests handler, which runs first
    and does not rely on this cascade — see handlers/guests.py for why.
    """
    report = PurgeReport(handler="invitations")

    result = await session.execute(
        delete(Invitation).where(Invitation.owner_id == user_id)
    )
    report.count("invitations", result.rowcount or 0)

    return report


@register_purge("feedback", order=TIER_AGGREGATE)
async def purge_feedback(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Product feedback the user submitted. Free text, owner-only, no retention basis."""
    report = PurgeReport(handler="feedback")

    result = await session.execute(
        delete(Feedback).where(Feedback.customer_id == user_id)
    )
    report.count("feedback", result.rowcount or 0)

    return report
