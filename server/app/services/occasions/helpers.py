"""
Occasions service — pure helper functions (no I/O, no side effects).
"""

from __future__ import annotations

from datetime import date


def calculate_celebration_progress(total_checklist: int, completed: int) -> float:
    """Return completed / total as a percentage (0.0 – 100.0), rounded to 2 dp.

    Returns 0.0 when *total_checklist* is zero to avoid division by zero.
    """
    if total_checklist <= 0:
        return 0.0
    pct = (completed / total_checklist) * 100.0
    return round(min(pct, 100.0), 2)


def sort_timeline_events(events: list) -> list:
    """Return *events* sorted ascending by ``occurred_at``.

    Events without an ``occurred_at`` attribute sort to the end.
    """
    return sorted(
        events,
        key=lambda e: getattr(e, "occurred_at", None) or date.max,
    )


def format_celebration_title(occasion_type: str, event_date: date) -> str:
    """Return a human-friendly celebration title.

    Example: ``format_celebration_title("Birthday", date(2026, 6, 20))``
    →  ``"Birthday – 20 Jun 2026"``
    """
    occasion_type = occasion_type.strip().title()
    formatted_date = event_date.strftime("%-d %b %Y") if hasattr(event_date, "strftime") else str(event_date)
    return f"{occasion_type} – {formatted_date}"
