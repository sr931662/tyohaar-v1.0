"""
Response shapes for the account deletion API.

The user-facing schema deliberately exposes the clocks. Someone who has asked
to be deleted is owed a straight answer to "when does this actually happen and
how long can I change my mind" — the dates are the answer, and hiding them
behind a status string would be worse.

`purge_report` is not exposed. It is internal compliance evidence and contains
handler names and table counts that mean nothing to a customer.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DeletionRequestChannel, DeletionRequestStatus


class DeletionRequestResponse(BaseModel):
    """What the account owner sees about their own deletion request."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: DeletionRequestStatus
    channel: DeletionRequestChannel
    requested_at: datetime
    #: Until this instant the account can still be restored. Null once the
    #: request has moved past the recovery window.
    recovery_ends_at: datetime | None = None
    #: The date by which the purge is committed to have completed.
    purge_due_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None


class PurgeRunResponse(BaseModel):
    """Summary of one scheduled purge run. Operational, not user-facing."""

    due: int
    purged: int
    incomplete: int
    failed: int
    guest_pii: dict[str, int] = {}
