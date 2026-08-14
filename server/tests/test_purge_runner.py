"""
Purge runner semantics.

These are the properties the deletion promise rests on, so they are tested
against the real runner with synthetic handlers rather than against the real
handlers with a synthetic runner. What matters here is not that any particular
table is emptied — that is each handler's business — but that the runner
never converts a failure into a success.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import pytest

from app.services.deletion import registry
from app.services.deletion.registry import (
    PurgeReport,
    register_purge,
    registered_handlers,
)
from app.services.deletion.runner import run_purge


class _FakeSession:
    """Minimal AsyncSession stand-in — the synthetic handlers never touch it."""

    def __init__(self) -> None:
        self.committed = 0

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:  # pragma: no cover - not exercised
        pass

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()


def _fake_factory():
    return _FakeSession()


@pytest.fixture
def clean_registry():
    """Swap the real registry out so tests do not depend on real handlers."""
    saved = dict(registry._REGISTRY)
    registry._REGISTRY.clear()
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(saved)


async def test_handlers_run_in_tier_order(clean_registry):
    order: list[str] = []

    @register_purge("late", order=900)
    async def late(session, user_id):
        order.append("late")
        return PurgeReport(handler="late")

    @register_purge("early", order=100)
    async def early(session, user_id):
        order.append("early")
        return PurgeReport(handler="early")

    await run_purge(uuid.uuid4(), session_factory=_fake_factory)

    assert order == ["early", "late"], (
        "external/session tiers must run before database tiers so a mid-run "
        "failure never deletes the last pointer to a live object"
    )


async def test_repeat_execution_is_safe(clean_registry):
    """Running twice must be safe and must not change the outcome."""
    calls: list[int] = []

    @register_purge("counting", order=100)
    async def counting(session, user_id):
        calls.append(1)
        report = PurgeReport(handler="counting")
        # A real handler deletes by predicate, so the second pass finds
        # nothing. Model that: rows on the first run, zero after.
        report.count("rows", 3 if len(calls) == 1 else 0)
        return report

    user_id = uuid.uuid4()
    first = await run_purge(user_id, session_factory=_fake_factory)
    second = await run_purge(user_id, session_factory=_fake_factory)

    assert first.ok and second.ok
    assert first.reports[0].counts == {"rows": 3}
    assert second.reports[0].counts == {}


async def test_missing_records_are_not_a_failure(clean_registry):
    """A user with no data at all purges successfully."""

    @register_purge("nothing_to_do", order=100)
    async def nothing_to_do(session, user_id):
        return PurgeReport(handler="nothing_to_do")

    result = await run_purge(uuid.uuid4(), session_factory=_fake_factory)

    assert result.ok
    assert result.errors == []


async def test_partial_failure_marks_run_not_ok(clean_registry):
    """One failing handler must not be absorbed into an overall success."""

    @register_purge("works", order=100)
    async def works(session, user_id):
        report = PurgeReport(handler="works")
        report.count("rows", 2)
        return report

    @register_purge("breaks", order=200)
    async def breaks(session, user_id):
        report = PurgeReport(handler="breaks")
        report.fail("storage object still present")
        return report

    result = await run_purge(uuid.uuid4(), session_factory=_fake_factory)

    assert result.ok is False
    assert any("storage object still present" in e for e in result.errors)


async def test_later_handlers_still_run_after_a_failure(clean_registry):
    """A failure in one tier must not strand the tiers below it."""
    ran: list[str] = []

    @register_purge("breaks", order=100)
    async def breaks(session, user_id):
        ran.append("breaks")
        report = PurgeReport(handler="breaks")
        report.fail("nope")
        return report

    @register_purge("after", order=200)
    async def after(session, user_id):
        ran.append("after")
        return PurgeReport(handler="after")

    result = await run_purge(uuid.uuid4(), session_factory=_fake_factory)

    assert ran == ["breaks", "after"]
    assert result.ok is False


async def test_raising_handler_is_contained_and_reported(clean_registry):
    """An unhandled exception fails that handler, not the whole run."""

    @register_purge("explodes", order=100)
    async def explodes(session, user_id):
        raise RuntimeError("customer +919876543210 blew up")

    @register_purge("survivor", order=200)
    async def survivor(session, user_id):
        return PurgeReport(handler="survivor")

    result = await run_purge(uuid.uuid4(), session_factory=_fake_factory)

    assert result.ok is False
    assert len(result.reports) == 2
    assert result.reports[1].ok is True

    # The retained report must not quote the exception message: it can contain
    # row values, and this report outlives the data it describes.
    serialised = str(result.as_dict())
    assert "919876543210" not in serialised
    assert "unhandled RuntimeError" in serialised


async def test_deferred_work_is_not_a_failure_but_is_recorded(clean_registry):
    """Work left undone on purpose is visible without failing the run."""

    @register_purge("pending_counsel", order=100)
    async def pending_counsel(session, user_id):
        report = PurgeReport(handler="pending_counsel")
        report.defer("invoice billing fields retained pending counsel")
        return report

    result = await run_purge(uuid.uuid4(), session_factory=_fake_factory)

    assert result.ok is True
    assert result.deferred == [
        "pending_counsel: invoice billing fields retained pending counsel"
    ]


async def test_duplicate_handler_name_is_rejected(clean_registry):
    @register_purge("dupe", order=100)
    async def one(session, user_id):
        return PurgeReport(handler="dupe")

    with pytest.raises(RuntimeError, match="Duplicate purge handler"):

        @register_purge("dupe", order=200)
        async def two(session, user_id):  # pragma: no cover
            return PurgeReport(handler="dupe")


async def test_real_handlers_are_registered_in_safe_order():
    """The shipped handler set must put external systems first and identity last."""
    names = [r.name for r in registered_handlers()]

    assert names, "no purge handlers registered"
    assert names[0] == "cloudinary_objects", (
        "external storage must be purged before any database row is removed"
    )
    assert names[-1] == "identity", (
        "the users tombstone must be written last, after every child row"
    )
    # Media rows must never be deleted before their objects.
    assert names.index("cloudinary_objects") < names.index("media_rows")
    # Guests must be purged before the celebrations they hang off, because
    # booked celebrations survive and would otherwise strand them.
    assert names.index("guests") < names.index("celebrations")
