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
