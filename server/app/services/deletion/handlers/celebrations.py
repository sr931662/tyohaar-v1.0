"""
Celebrations — deleted when free, sanitised when booked.

`bookings.celebration_id` is a RESTRICT foreign key declared NOT NULL, and
bookings are retained for the financial window. Postgres will therefore refuse
to delete any celebration that was ever booked, for as long as its booking
survives. That is not a constraint we can engineer around, and deleting the
booking to free the celebration would destroy a record we are required to keep.

So celebrations split in two:

  * **Unbooked** — deleted outright. Nothing references them.
  * **Booked** — the row survives as the booking's context, with every
    personal and presentational field cleared. What remains is structural:
    which occasion type, which date, how many guests, what it cost. None of
    that identifies a person once the profile, guests and free text are gone.

The alternative — leaving a booked celebration intact because it "belongs to"
a retained booking — would keep the venue address, the event title and the
host's own notes indefinitely. That is exactly the failure mode the policy
exists to prevent: retaining a transaction must not mean retaining a life.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bookings.booking import Booking
from app.models.occasions.celebration import Celebration
from app.services.deletion.registry import (
    TIER_AGGREGATE,
    PurgeReport,
    register_purge,
)

#: Placeholder for `title`, which is NOT NULL and so cannot simply be cleared.
#: It carries no personal data and is deliberately recognisable in support
#: tooling as a sanitised row rather than a real celebration name.
SANITISED_TITLE = "Deleted celebration"

#: Fields cleared on a surviving celebration. Everything here is either
#: personal (venue address, coordinates), presentational (theme colours) or
#: free text the host wrote. `title` is replaced rather than nulled.
_SANITISED_FIELDS: dict[str, object] = {
    "title": SANITISED_TITLE,
    "description": None,
    "venue_name": None,
    "venue_address": None,
    "venue_address_id": None,
    "latitude": None,
    "longitude": None,
    "special_instructions": None,
    "custom_theme_colors": None,
}


@register_purge("celebrations", order=TIER_AGGREGATE + 10)
async def purge_celebrations(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    report = PurgeReport(handler="celebrations")

    owned = list(
        (
            await session.execute(
                select(Celebration.id).where(Celebration.customer_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    if not owned:
        return report

    booked = set(
        (
            await session.execute(
                select(Booking.celebration_id).where(
                    Booking.celebration_id.in_(owned)
                )
            )
        )
        .scalars()
        .all()
    )
    unbooked = [cid for cid in owned if cid not in booked]

    if booked:
        result = await session.execute(
            update(Celebration)
            .where(Celebration.id.in_(booked))
            .values(**_SANITISED_FIELDS)
        )
        report.count("celebrations_sanitised", result.rowcount or 0)

    if unbooked:
        result = await session.execute(
            delete(Celebration).where(Celebration.id.in_(unbooked))
        )
        report.count("celebrations_deleted", result.rowcount or 0)

    return report
