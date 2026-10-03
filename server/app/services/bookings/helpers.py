from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP


def calculate_booking_total(items: list[dict]) -> Decimal:
    """Sum final_price for each item dict."""
    total = Decimal("0.00")
    for item in items:
        total += Decimal(str(item.get("final_price", "0")))
    return total


def calculate_cancellation_fee(total: Decimal, percentage: Decimal) -> Decimal:
    """Return fee = total * percentage, rounded to 2dp."""
    return (total * percentage).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_refund_amount(total: Decimal, fee: Decimal) -> Decimal:
    """Return refund = total - fee (floored at zero)."""
    refund = total - fee
    return max(Decimal("0.00"), refund)


def is_booking_cancellable(event_date: datetime, cutoff_hours: int) -> bool:
    """Return True if now is at least cutoff_hours before event_date."""
    from datetime import timedelta
    now = datetime.now(tz=timezone.utc)
    # Ensure event_date is offset-aware
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    return now <= event_date - timedelta(hours=cutoff_hours)


def is_booking_reschedule_eligible(event_date: datetime, cutoff_hours: int) -> bool:
    """Return True if now is at least cutoff_hours before event_date."""
    return is_booking_cancellable(event_date, cutoff_hours)


def validate_status_transition(current: str, next_status: str) -> bool:
    """Return True if the transition from current → next_status is valid."""
    from app.services.bookings.constants import VALID_STATUS_TRANSITIONS
    allowed = VALID_STATUS_TRANSITIONS.get(current.lower(), set())
    return next_status.lower() in allowed


def generate_booking_reference() -> str:
    """Return 'TYO' + 8 random uppercase alphanumeric characters."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=8))
    return f"TYO{suffix}"


# ── Customisable lines ────────────────────────────────────────────────────────
#
# A customisable package line takes one of two shapes, decided by the line
# itself rather than by anything named here, so a vendor adding an add-on in
# the portal needs no code change:
#
#   * a fixed `choices` list — the customer picks one of the vendor's options;
#   * no `choices` — the line takes a NUMBER. The vendor stocks digits as
#     physical characters (a marquee letter set), so the customer dials in
#     "20" and the vendor brings a 2 and a 0: two characters, billed at the
#     line's base price each.
#
# Both rules live here rather than inside create_booking so the booking path
# and its tests exercise the same code.


def is_numeric_line(line) -> bool:
    """True when a customisable line takes a dialled-in number, not a choice."""
    return bool(getattr(line, "is_customizable", False)) and not (
        getattr(line, "choices", None) or []
    )


def resolve_customization(line, supplied: dict, *, max_length: int, max_digits: int) -> str | None:
    """
    What the customer specified for one line, or None.

    A `choices` line must match one of the vendor's options, so a tampered
    client cannot order something never offered. A numeric line keeps only
    digits — everything else is dropped rather than ordered — capped at
    `max_digits`, since every digit is a character the vendor carries and a
    charge on the line.
    """
    value = supplied.get(str(line.id))
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None

    offered = getattr(line, "choices", None) or []
    if offered:
        # Still bounded: a choice comes from the vendor, and the column it
        # lands in is not unlimited.
        return value[:max_length] if value in offered else None

    if not getattr(line, "is_customizable", False):
        return None

    digits = "".join(ch for ch in value if ch in "0123456789")
    if not digits:
        return None
    return digits[:max_digits]


def digit_quantity(line, digits: str) -> int:
    """
    Characters ordered on a numeric line: one per digit.

    "20" is a 2 and a 0, so it bills at 2 x the line's base price. Still
    capped by max_quantity — a vendor who owns three characters cannot
    supply four.
    """
    qty = len(digits)
    max_quantity = getattr(line, "max_quantity", None)
    if max_quantity is not None:
        qty = min(qty, max_quantity)
    return max(qty, 1)
