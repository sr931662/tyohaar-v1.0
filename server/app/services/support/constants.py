from __future__ import annotations

MAX_MESSAGES_PER_TICKET = 200
MAX_ATTACHMENTS_PER_MESSAGE = 5
MAX_ATTACHMENT_SIZE_MB = 10
TICKET_AUTO_CLOSE_DAYS = 7  # close resolved tickets after 7 days
MAX_OPEN_TICKETS_PER_USER = 5
VALID_TICKET_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "resolved", "closed"},
    "in_progress": {"resolved", "closed", "open"},
    "resolved": {"closed", "open"},  # can reopen
    "closed": {"open"},  # can reopen
}
