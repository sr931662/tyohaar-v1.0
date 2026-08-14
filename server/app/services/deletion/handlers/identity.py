"""
Tier: identity — the last handler to run.

Twenty tables hold `RESTRICT` foreign keys onto `users.id` declared NOT NULL,
several of them (`invoices`, `payments`, `bookings`) pointing at records we are
required to retain. Postgres will therefore never allow the row to be deleted,
and deleting the children to free it would destroy records we must keep.

Deletion here means **erasing the personal data from a surviving row**, not
removing the row. What remains is an opaque key: an id, timestamps, and the
status flags that keep the foreign keys valid. It holds no name, no contact
detail, no credential, and nothing that could rebuild the profile.

This is a real limitation and it is stated plainly in the privacy policy and
on the delete-account page rather than being papered over — a user who is told
"your record is gone" and later discovers an id is still referenced by an
invoice has been misled, even though every piece of their personal data was in
fact erased.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus
from app.models.users.address import UserAddress
from app.models.users.profile import UserProfile
from app.models.users.user import User
from app.services.deletion.registry import (
    TIER_TOMBSTONE,
    PurgeReport,
    register_purge,
)


@register_purge("identity", order=TIER_TOMBSTONE)
async def purge_identity(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    report = PurgeReport(handler="identity")

    # Addresses and the profile are CASCADE children — they are deleted
    # outright, not emptied. Nothing retains a reference to them.
    result = await session.execute(
        delete(UserAddress).where(UserAddress.user_id == user_id)
    )
    report.count("user_addresses", result.rowcount or 0)

    result = await session.execute(
        delete(UserProfile).where(UserProfile.user_id == user_id)
    )
    report.count("user_profiles", result.rowcount or 0)

    # The tombstone. Every column that carries or reconstructs identity is
    # cleared in one statement.
    #
    # `phone` is NOT NULL and UNIQUE, so it cannot be nulled — it is
    # overwritten with a value derived from the (already opaque) primary key.
    # That satisfies both constraints without retaining anything: the
    # replacement is not a phone number and cannot be dialled, and it reveals
    # nothing the row's own id did not already reveal.
    #
    # The column is VARCHAR(15), which is the whole reason for the shape here:
    # 'x' plus 14 hex digits is exactly 15 characters. Those 56 bits make a
    # collision between two tombstoned users vanishingly unlikely, and deriving
    # it from the id rather than randomly keeps the purge idempotent — a second
    # run writes the identical value instead of a fresh one.
    tombstone_phone = f"x{user_id.int & 0xFFFFFFFFFFFFFF:014x}"

    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            phone=tombstone_phone,
            email=None,
            username=None,
            full_name=None,
            first_name=None,
            middle_name=None,
            last_name=None,
            password_hash=None,
            phone_verified=False,
            email_verified=False,
            mfa_enabled=False,
            # Deactivation is expressed by account_status + deleted_at. The
            # real User model has no is_active column — app/models/user.py is a
            # legacy stub that also declares __tablename__ = "users" and does.
            account_status=AccountStatus.DEACTIVATED,
            deleted_at=datetime.now(tz=timezone.utc),
            last_login_at=None,
            account_locked_until=None,
            failed_login_count=0,
        )
    )
    report.count("users_tombstoned", result.rowcount or 0)

    if not result.rowcount:
        # The user row is already gone or was never there. Not an error — a
        # re-run of a completed purge lands here — but worth recording so the
        # report distinguishes "nothing to do" from "did the work".
        report.count("users_already_absent", 1)

    return report
