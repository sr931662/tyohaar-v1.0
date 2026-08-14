"""
Purge handler registry.

Each domain owns one handler. The runner iterates whatever is registered, so
adding a module means adding a handler — never editing a growing central
function that everyone has to touch and nobody dares refactor.

Contract every handler must honour:

  * **Idempotent.** Running twice must be safe and must produce the same end
    state. Handlers delete by predicate, never by remembered offset.

  * **Honest.** A handler returns `ok=False` when it could not finish. It must
    never report success for work it did not do. The runner marks the whole
    request INCOMPLETE if any handler fails, and INCOMPLETE never becomes
    PURGED without a successful re-run.

  * **Ordered.** `order` places the handler in a tier. External systems run
    before database rows so that a mid-run failure leaves a recoverable
    pointer to an orphaned object rather than the reverse.

  * **Counts only.** `PurgeReport.details` carries names and numbers. Never
    sample values, never deleted content — this report is retained as
    compliance evidence long after the data is gone.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Protocol

from sqlalchemy.ext.asyncio import AsyncSession


# ── Tiers ─────────────────────────────────────────────────────────────────────
# Lower runs first. Gaps are deliberate so a handler can be slotted between
# two existing tiers without renumbering everything.

TIER_EXTERNAL = 100      # Cloudinary, FCM — anything outside our database
TIER_SESSION = 200       # sessions, tokens, devices (also runs at Day 0)
TIER_LEAF = 300          # rows nothing else references
TIER_AGGREGATE = 400     # owned parents: celebrations, invitations, budgets
TIER_SANITISE = 500      # rows that survive with fields cleared
TIER_TOMBSTONE = 600     # the users row itself — always last


@dataclass
class PurgeReport:
    """Outcome of one handler for one user."""

    handler: str
    ok: bool = True
    #: table/object name → number of rows or objects affected
    counts: dict[str, int] = field(default_factory=dict)
    #: Human-readable failure reasons. Never include personal data.
    errors: list[str] = field(default_factory=list)
    #: Work deliberately not done, e.g. a field awaiting counsel. Not a failure,
    #: but it means no deletion claim may be made about that data.
    deferred: list[str] = field(default_factory=list)

    def count(self, name: str, n: int) -> None:
        if n:
            self.counts[name] = self.counts.get(name, 0) + n

    def fail(self, reason: str) -> None:
        self.ok = False
        self.errors.append(reason)

    def defer(self, what: str) -> None:
        self.deferred.append(what)

    def as_dict(self) -> dict:
        return {
            "handler": self.handler,
            "ok": self.ok,
            "counts": self.counts,
            "errors": self.errors,
            "deferred": self.deferred,
        }


class PurgeHandler(Protocol):
    """Signature every handler implements."""

    async def __call__(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> PurgeReport: ...


@dataclass(frozen=True)
class _Registration:
    name: str
    order: int
    fn: PurgeHandler


_REGISTRY: dict[str, _Registration] = {}


def register_purge(
    name: str, order: int
) -> Callable[[PurgeHandler], PurgeHandler]:
    """Decorator registering a purge handler under a stable name.

    The name appears verbatim in the retained purge report, so treat it as
    part of the compliance record and do not rename casually.
    """

    def decorator(fn: PurgeHandler) -> PurgeHandler:
        if name in _REGISTRY:
            raise RuntimeError(f"Duplicate purge handler registered: {name!r}")
        _REGISTRY[name] = _Registration(name=name, order=order, fn=fn)
        return fn

    return decorator


def registered_handlers() -> list[_Registration]:
    """All handlers, in execution order."""
    return sorted(_REGISTRY.values(), key=lambda r: (r.order, r.name))


def handler_names() -> list[str]:
    return [r.name for r in registered_handlers()]


def clear_registry_for_tests() -> None:
    """Test-only hook. Never call from application code."""
    _REGISTRY.clear()
