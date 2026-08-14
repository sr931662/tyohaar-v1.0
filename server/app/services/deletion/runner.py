"""
Purge runner — executes registered handlers for one deletion request.

Design notes that matter more than they look:

**Per-handler transactions.** Each handler commits on its own. A single giant
transaction would be tidier but would mean one late failure discards hours of
completed deletion work, and the retry would then redo external calls that had
already succeeded. Committing per handler makes the run resumable: whatever
finished stays finished.

**Failure does not abort the run.** A handler that fails records why and the
run continues to the next. Stopping early would leave later tiers untouched
for a reason unrelated to them, and the user would stay less deleted than they
could have been. The request ends INCOMPLETE and is retried.

**INCOMPLETE never silently becomes PURGED.** Only a run in which every
handler reported success sets PURGED. That is the property the whole design
exists to protect: the system must never claim a deletion it did not perform.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.deletion import handlers as _handlers  # noqa: F401 - registers
from app.services.deletion.registry import PurgeReport, registered_handlers

logger = logging.getLogger(__name__)


@dataclass
class PurgeRunResult:
    """Aggregate outcome of one full pass over the handlers."""

    user_id: uuid.UUID
    reports: list[PurgeReport] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.reports)

    @property
    def deferred(self) -> list[str]:
        out: list[str] = []
        for r in self.reports:
            out.extend(f"{r.handler}: {d}" for d in r.deferred)
        return out

    @property
    def errors(self) -> list[str]:
        out: list[str] = []
        for r in self.reports:
            out.extend(f"{r.handler}: {e}" for e in r.errors)
        return out

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "ran_at": datetime.now(tz=timezone.utc).isoformat(),
            "handlers": [r.as_dict() for r in self.reports],
            "deferred": self.deferred,
            "errors": self.errors,
        }


async def run_purge(
    user_id: uuid.UUID,
    *,
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
) -> PurgeRunResult:
    """Run every registered handler for one user, in tier order.

    Safe to call repeatedly. Handlers delete by predicate, so a second run over
    an already-purged user finds nothing and reports success — which is what
    makes retrying a partially failed request trivial.
    """
    result = PurgeRunResult(user_id=user_id)

    for registration in registered_handlers():
        try:
            async with session_factory() as session:
                report = await registration.fn(session, user_id)
                await session.commit()
        except Exception as exc:  # noqa: BLE001 - one handler must not sink the run
            logger.exception(
                "purge handler failed", extra={"handler": registration.name}
            )
            report = PurgeReport(handler=registration.name)
            # Only the exception type is recorded. Messages can quote row
            # values, and this report is retained as compliance evidence long
            # after the data itself is gone.
            report.fail(f"unhandled {type(exc).__name__}")

        result.reports.append(report)

    return result
