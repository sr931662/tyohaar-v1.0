"""
Tier: session & access.

Runs at Day 0, the moment a deletion request is verified — not at Day 14.
Everything here is a live path to the account or the person's device, and
none of it has any reason to outlive the request by a fortnight.

Re-run at purge time as well, so a session created between Day 0 and Day 14
by some path we did not anticipate is still cleared.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.otp import OTPRecord
from app.models.auth.refresh_token import RefreshToken
from app.models.auth.session import UserSession
from app.models.users.device import UserDevice
from app.services.deletion.registry import (
    TIER_SESSION,
    PurgeReport,
    register_purge,
)


@register_purge("session_access", order=TIER_SESSION)
async def purge_session_access(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    report = PurgeReport(handler="session_access")

    # Refresh tokens first: they are FK-bound to sessions, and deleting the
    # session row out from under them would rely on cascade ordering we do
    # not need to depend on.
    result = await session.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user_id)
    )
    report.count("refresh_tokens", result.rowcount or 0)

    result = await session.execute(
        delete(UserSession).where(UserSession.user_id == user_id)
    )
    report.count("user_sessions", result.rowcount or 0)

    result = await session.execute(
        delete(OTPRecord).where(OTPRecord.user_id == user_id)
    )
    report.count("otp_records", result.rowcount or 0)

    # Device rows carry the push token. Removing them is what actually stops
    # notifications reaching a handset; unregistering the token with FCM is a
    # separate external handler and both are required.
    result = await session.execute(
        delete(UserDevice).where(UserDevice.user_id == user_id)
    )
    report.count("user_devices", result.rowcount or 0)

    return report
