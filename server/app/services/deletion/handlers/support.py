"""
Tier: support conversations.

Ticket bodies and attachments are not operational metadata. Customers
routinely paste addresses, phone numbers and photos into them, so the whole
conversation is treated as personal data belonging to the account owner.

`support_messages.ticket_id` is RESTRICT, so messages must be removed before
their ticket. Attachment objects are deleted by the external handler; only the
rows are removed here.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media.unresolved_asset import UnresolvedMediaAsset
from app.models.support.attachment import SupportAttachment
from app.models.support.message import SupportMessage
from app.models.support.ticket import SupportTicket
from app.services.deletion.registry import (
    TIER_AGGREGATE,
    PurgeReport,
    register_purge,
)


@register_purge("support", order=TIER_AGGREGATE + 30)
async def purge_support(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    report = PurgeReport(handler="support")

    ticket_ids = list(
        (
            await session.execute(
                select(SupportTicket.id).where(SupportTicket.customer_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    if not ticket_ids:
        return report

    # An attachment whose object could not be destroyed keeps its row, and
    # therefore keeps its ticket — the same pointer rule as media.
    blocked = set(
        (
            await session.execute(
                select(UnresolvedMediaAsset.media_id).where(
                    UnresolvedMediaAsset.owner_id == user_id,
                    UnresolvedMediaAsset.media_kind == "support_attachment",
                    UnresolvedMediaAsset.resolved_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )

    stmt = delete(SupportAttachment).where(
        SupportAttachment.ticket_id.in_(ticket_ids)
    )
    if blocked:
        stmt = stmt.where(SupportAttachment.id.notin_(blocked))
    result = await session.execute(stmt)
    report.count("support_attachments", result.rowcount or 0)

    if blocked:
        report.count("support_attachments_retained_unresolved", len(blocked))
        report.fail(
            f"{len(blocked)} support attachment row(s) kept: their storage "
            "objects could not be deleted"
        )
        # Leave the owning tickets in place too — deleting them would orphan
        # the attachment rows we just deliberately preserved.
        return report

    result = await session.execute(
        delete(SupportMessage).where(SupportMessage.ticket_id.in_(ticket_ids))
    )
    report.count("support_messages", result.rowcount or 0)

    result = await session.execute(
        delete(SupportTicket).where(SupportTicket.id.in_(ticket_ids))
    )
    report.count("support_tickets", result.rowcount or 0)

    return report
