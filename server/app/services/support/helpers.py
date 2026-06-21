from __future__ import annotations

import random

from app.services.support.constants import VALID_TICKET_STATUS_TRANSITIONS

_STATUS_LABELS: dict[str, str] = {
    "open": "Open",
    "in_progress": "In Progress",
    "pending": "Pending",
    "resolved": "Resolved",
    "closed": "Closed",
}


def generate_ticket_number() -> str:
    """Return 'TKT' followed by 8 random digits."""
    digits = "".join(str(random.randint(0, 9)) for _ in range(8))
    return f"TKT{digits}"


def is_ticket_status_transition_valid(current: str, next_status: str) -> bool:
    allowed = VALID_TICKET_STATUS_TRANSITIONS.get(current.lower(), set())
    return next_status.lower() in allowed


def format_ticket_status_label(status: str) -> str:
    return _STATUS_LABELS.get(status.lower(), status.replace("_", " ").title())


def truncate_message(text: str, max_length: int = 2000) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"
