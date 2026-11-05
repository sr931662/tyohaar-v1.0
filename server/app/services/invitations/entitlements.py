"""
What an event may use — one answer for booked and independent events alike.

There is no plan or subscription system to plug into yet (memberships were
removed in c1d2e3f4a5b6), so entitlements are resolved from, in order:

  1. Defaults for the event's tier below.
  2. ``invitations.entitlements`` in app_settings — admin-editable JSON, so
     pricing can change without a deployment:
       {"standalone": {...}, "booked": {...}, "packages": {"<package id>": {...}}}
  3. For a booked event, that JSON's entry for the booked package.

A booking only counts once it is confirmed: a pending or cancelled booking
leaves the event on the standalone tier. ``automated_reminders`` additionally
requires the WhatsApp Business Platform to be configured, whatever the tier
says, because granting a feature nothing can deliver would be a lie.
"""

from __future__ import annotations

import json
import logging

from app.models.enums import BookingStatus, EventSource
from app.schemas.events import Entitlements
from app.services.invitations import whatsapp_cloud

logger = logging.getLogger(__name__)

SETTING_KEY = "invitations.entitlements"

ACTIVE_BOOKING_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.IN_PROGRESS,
    BookingStatus.COMPLETED,
    BookingStatus.RESCHEDULED,
)

_STANDALONE = Entitlements(vendor_reports=False, automated_reminders=False)
_BOOKED = Entitlements(vendor_reports=True, automated_reminders=False)


def _merge(base: Entitlements, override: object) -> Entitlements:
    if not isinstance(override, dict):
        return base
    known = {k: bool(v) for k, v in override.items() if k in Entitlements.model_fields}
    return base.model_copy(update=known)


def resolve(*, booked: bool, platform: dict | None, package_id: str | None = None) -> Entitlements:
    """Pure: the same inputs always give the same answer."""
    result = _BOOKED if booked else _STANDALONE
    if isinstance(platform, dict):
        result = _merge(result, platform.get("booked" if booked else "standalone"))
        packages = platform.get("packages")
        if booked and package_id and isinstance(packages, dict):
            result = _merge(result, packages.get(package_id))
    if result.automated_reminders and not whatsapp_cloud.is_configured():
        result = result.model_copy(update={"automated_reminders": False})
    return result


async def for_event(uow, celebration) -> Entitlements:
    from sqlalchemy import select

    from app.models.bookings.booking import Booking

    platform = None
    setting = await uow.common.settings.get_by_key(SETTING_KEY)
    if setting is not None and setting.value:
        try:
            platform = json.loads(setting.value)
        except (ValueError, TypeError):
            logger.warning("Ignoring malformed %s setting", SETTING_KEY)

    package_id = None
    booked = False
    if celebration.event_source is EventSource.TYOHAAR_BOOKING:
        package_id = (await uow.session.execute(
            select(Booking.package_id)
            .where(
                Booking.celebration_id == celebration.id,
                Booking.booking_status.in_(ACTIVE_BOOKING_STATUSES),
            )
            .order_by(Booking.created_at.asc())
            .limit(1)
        )).scalar_one_or_none()
        booked = package_id is not None
    return resolve(booked=booked, platform=platform, package_id=str(package_id) if package_id else None)
