from __future__ import annotations

from decimal import Decimal

BOOKING_CUTOFF_HOURS = 24
CANCELLATION_WINDOW_HOURS = 48
RESCHEDULE_WINDOW_HOURS = 48
MAX_BOOKING_ITEMS = 10
CANCELLATION_FEE_PERCENTAGE = Decimal("0.10")

VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "refunded": set(),
    "disputed": {"confirmed", "cancelled"},
    "no_show": set(),
    "rescheduled": {"confirmed", "cancelled"},
}
