"""
End-to-end deletion lifecycle against a real database.

Skipped automatically when no Postgres is reachable, because the schema uses
PGUUID and JSONB throughout and cannot be faked on SQLite. Point
`TEST_DATABASE_URL` at a scratch database to run them:

    TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tyohaar_test \
        python -m pytest tests/test_deletion_lifecycle_integration.py

These cover the behaviours that only exist once real tables and real foreign
keys are involved — the RESTRICT constraints are the entire reason the
tombstone design exists, and they cannot be exercised without them.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models import *  # noqa: F401,F403 - registers every table on Base
from app.models.enums import (
    AccountStatus,
    DeletionRequestStatus,
    UserRole,
    UserType,
)
from app.models.users.address import UserAddress
from app.models.users.deletion_request import DeletionRequest
from app.models.users.profile import UserProfile
from app.models.users.user import User
from app.services.deletion.service import DeletionService

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

# The engine fixture is module-scoped (see below), so every coroutine in this
# module has to share one event loop — asyncpg connections cannot cross loops.
pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.skipif(
        not TEST_DATABASE_URL,
        reason="TEST_DATABASE_URL not set — deletion integration tests need Postgres",
    ),
]

#: These fixtures call `drop_all`. Pointed at the wrong database that destroys
#: every table in it, so the target must prove it is disposable before the
#: fixture will touch it. The check is deliberately dumb and unbypassable:
#: the database *name* has to say so.
_REQUIRED_NAME_MARKERS = ("test", "staging", "scratch")


def _configured_database_target() -> tuple[str, str] | None:
    """The (host, database) this deployment actually runs on, read from .env.

    Read from disk rather than from `settings` so the check still works when
    the test process has been given a different DATABASE_URL — which is
    exactly the situation where someone is most likely to get this wrong.
    """
    from urllib.parse import urlparse

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            raw = line.split("=", 1)[1].strip().strip('"').strip("'")
            parsed = urlparse(raw.replace("postgresql+asyncpg://", "postgresql://"))
            return (
                (parsed.hostname or "").lower(),
                (parsed.path or "").lstrip("/").split("?")[0].lower(),
            )
    return None


def _assert_disposable(url: str) -> None:
    """Refuse to run against anything that is not provably a scratch database.

    A missed guard here is not a failing test — it is a destroyed database.
    Three independent checks, all of which must pass, and none of which can be
    switched off by an environment variable:

      1. The target must be the database this run created for itself, never
         the one the deployment actually uses.
      2. Its name must say it is disposable.
      3. The process must not be running in a production context.

    Check 1 is the one that matters. The other two are there for the case
    where someone edits or misreads it.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
    name = (parsed.path or "").lstrip("/").split("?")[0].lower()
    host = (parsed.hostname or "").lower()

    # 1 — never the deployment's own database, whatever it is called.
    configured = _configured_database_target()
    if configured is not None and (host, name) == configured:
        pytest.exit(
            f"REFUSING TO RUN: {name!r} on {host!r} is the database configured "
            "in server/.env — the one this deployment actually uses. These "
            "tests DROP every table. Create a separate scratch database.",
            returncode=2,
        )

    # 2 — the name has to say it is throwaway.
    if not any(marker in name for marker in _REQUIRED_NAME_MARKERS):
        pytest.exit(
            f"REFUSING TO RUN: database {name!r} on {host!r} has a name "
            f"containing none of {_REQUIRED_NAME_MARKERS}. These tests DROP "
            "every table. Point them at a disposable database.",
            returncode=2,
        )

    # 3 — and not from a production process.
    if os.environ.get("ENVIRONMENT", "").lower().startswith("prod"):
        pytest.exit(
            "REFUSING TO RUN: ENVIRONMENT is production. Run these against a "
            "staging or scratch environment only.",
            returncode=2,
        )


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def engine():
    """Build the schema once for the whole module.

    Creating and dropping 105 tables per test against a hosted Postgres takes
    minutes, so the schema is built once and each test gets a clean slate from
    the `clean_tables` fixture instead. The guard still runs first, before any
    connection is opened.
    """
    _assert_disposable(TEST_DATABASE_URL)

    from sqlalchemy import text

    # Connect exactly the way the application does. asyncpg rejects libpq's
    # `sslmode` as a connect keyword, so the project converts it to an
    # SSLContext; a test that builds its own URL instead will fail against any
    # managed Postgres that requires TLS.
    from app.db.session import _build_engine_args

    url, connect_args = _build_engine_args(TEST_DATABASE_URL)
    engine = create_async_engine(url, connect_args=connect_args, future=True)
    async with engine.begin() as conn:
        # Reset the schema wholesale rather than metadata.drop_all. The scratch
        # database may already carry an alembic-built schema, and drop_all only
        # knows about objects declared on the metadata — leftover indexes and
        # the alembic_version table survive it and collide on create_all.
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

        # Column comments are documentation and irrelevant to behaviour, but
        # create_all emits a separate COMMENT ON COLUMN round trip for each of
        # the ~2000 commented columns in this schema. Against a hosted Postgres
        # that alone costs ten minutes per run. Drop them for the test build.
        _comments = {}
        for table in Base.metadata.tables.values():
            _comments[table] = (table.comment, {c: c.comment for c in table.columns})
            table.comment = None
            for column in table.columns:
                column.comment = None
        try:
            await conn.run_sync(Base.metadata.create_all)
        finally:
            for table, (tcomment, ccomments) in _comments.items():
                table.comment = tcomment
                for column, comment in ccomments.items():
                    column.comment = comment
    yield engine
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True, loop_scope="module")
async def clean_tables(engine):
    """Empty every table between tests.

    One TRUNCATE ... CASCADE over the whole schema is dramatically faster than
    rebuilding it, and CASCADE means the RESTRICT foreign keys the purge has to
    respect do not get in the way of the reset — only of the code under test,
    which is the point.
    """
    from sqlalchemy import text

    # Truncating `users` CASCADE reaches every table that references it, which
    # is the whole graph these tests build. Naming all 105 tables instead costs
    # a great deal of time against a hosted Postgres for no extra cleanliness.
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE users, deletion_requests RESTART IDENTITY CASCADE")
        )
    yield


@pytest.fixture(autouse=True)
def stub_storage(monkeypatch):
    """Make the storage provider succeed for the lifecycle tests.

    Cloudinary has no credentials in CI, so without this every purge would end
    INCOMPLETE and these tests would be measuring the absence of a third-party
    account rather than the deletion lifecycle. The opposite case — storage
    unreachable — is asserted explicitly in
    `test_unreachable_storage_yields_incomplete`, because that honesty property
    matters more than any of the happy paths here.
    """
    from app.services.deletion.handlers import external

    async def _destroy(public_id: str, *, resource_type: str = "image") -> bool:
        return True

    monkeypatch.setattr(external.cloudinary_client, "destroy_asset", _destroy)


@pytest_asyncio.fixture(loop_scope="module")
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(loop_scope="module")
async def service(session_factory):
    return DeletionService(session_factory)


async def _make_user(session_factory, *, role: UserRole = UserRole.CUSTOMER) -> User:
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            phone=f"+9198{uuid.uuid4().int % 100000000:08d}",
            email=f"{uuid.uuid4().hex[:10]}@example.com",
            full_name="Test Person",
            first_name="Test",
            last_name="Person",
            role=role,
            user_type=UserType.INDIVIDUAL,
            account_status=AccountStatus.ACTIVE,
        )
        session.add(user)
        session.add(
            UserProfile(
                id=uuid.uuid4(),
                user_id=user.id,
                city="Delhi",
                profile_photo_url="https://res.cloudinary.com/d/image/upload/v1/a/b.jpg",
                profile_photo_public_id="a/b",
            )
        )
        session.add(
            UserAddress(
                id=uuid.uuid4(),
                user_id=user.id,
                recipient_name="Test Person",
                recipient_phone="+919876543210",
                address_line_1="12 Example Road",
                city="Delhi",
                state="Delhi",
                postal_code="110001",
            )
        )
        await session.commit()
        return user


class TestRequestAndDayZero:
    async def test_request_deactivates_immediately(self, service, session_factory):
        user = await _make_user(session_factory)

        request = await service.request_deletion(user_id=user.id)

        assert request.status == DeletionRequestStatus.RECOVERABLE
        assert request.verified_at is not None
        assert request.recovery_ends_at > datetime.now(tz=timezone.utc)

        async with session_factory() as session:
            refreshed = await session.get(User, user.id)
            assert refreshed.account_status == AccountStatus.DEACTIVATED
            assert refreshed.deleted_at is None  # nothing destroyed at Day 0
            # Day 0 stops access but destroys nothing.
            assert refreshed.full_name == "Test Person"

    async def test_request_stores_no_raw_identifier(self, service, session_factory):
        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)

        assert user.phone not in request.identifier_hash
        assert user.email not in request.identifier_hash
        assert len(request.identifier_hash) == 64

    async def test_duplicate_request_is_rejected(self, service, session_factory):
        from app.services.exceptions import ConflictError

        user = await _make_user(session_factory)
        await service.request_deletion(user_id=user.id)

        with pytest.raises(ConflictError):
            await service.request_deletion(user_id=user.id)

    @pytest.mark.parametrize(
        "role", [UserRole.VENDOR, UserRole.ADMIN, UserRole.SUPER_ADMIN]
    )
    async def test_vendor_and_admin_accounts_are_refused(
        self, service, session_factory, role
    ):
        from app.services.exceptions import ValidationError

        user = await _make_user(session_factory, role=role)

        with pytest.raises(ValidationError):
            await service.request_deletion(user_id=user.id)


class TestRecovery:
    async def test_cancel_restores_the_account(self, service, session_factory):
        user = await _make_user(session_factory)
        await service.request_deletion(user_id=user.id)

        request = await service.cancel_deletion(user_id=user.id)

        assert request.status == DeletionRequestStatus.CANCELLED
        async with session_factory() as session:
            refreshed = await session.get(User, user.id)
            assert refreshed.account_status == AccountStatus.ACTIVE
            assert refreshed.deleted_at is None

    async def test_cancelling_allows_a_fresh_request_later(
        self, service, session_factory
    ):
        user = await _make_user(session_factory)
        await service.request_deletion(user_id=user.id)
        await service.cancel_deletion(user_id=user.id)

        again = await service.request_deletion(user_id=user.id)
        assert again.status == DeletionRequestStatus.RECOVERABLE

    async def test_request_inside_window_is_not_due(self, service, session_factory):
        user = await _make_user(session_factory)
        await service.request_deletion(user_id=user.id)

        assert await service.find_due() == []

    async def test_request_past_window_is_due(self, service, session_factory):
        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)

        future = datetime.now(tz=timezone.utc) + timedelta(days=15)
        due = await service.find_due(now=future)
        assert request.id in due

    async def test_legal_hold_suspends_the_purge(self, service, session_factory):
        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)

        async with session_factory() as session:
            held = await session.get(DeletionRequest, request.id)
            held.legal_hold_until = datetime.now(tz=timezone.utc) + timedelta(days=90)
            held.legal_hold_reason = "open chargeback"
            await session.commit()

        future = datetime.now(tz=timezone.utc) + timedelta(days=15)
        assert request.id not in await service.find_due(now=future)


class TestPurge:
    async def test_purge_erases_pii_and_leaves_a_tombstone(
        self, service, session_factory
    ):
        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)

        result = await service.purge_request(request_id=request.id)

        assert result.status == DeletionRequestStatus.PURGED
        assert result.user_id is None, "the completed record must not name the person"

        async with session_factory() as session:
            tombstone = await session.get(User, user.id)
            assert tombstone is not None, "the row survives — RESTRICT FKs require it"
            assert tombstone.email is None
            assert tombstone.full_name is None
            assert tombstone.first_name is None
            assert tombstone.last_name is None
            assert tombstone.username is None
            assert tombstone.password_hash is None
            assert tombstone.phone.startswith("x") and len(tombstone.phone) == 15
            assert tombstone.account_status == AccountStatus.DEACTIVATED
            assert tombstone.deleted_at is not None

            profiles = (
                await session.execute(
                    select(UserProfile).where(UserProfile.user_id == user.id)
                )
            ).scalars().all()
            assert profiles == []

            addresses = (
                await session.execute(
                    select(UserAddress).where(UserAddress.user_id == user.id)
                )
            ).scalars().all()
            assert addresses == []

    async def test_purge_is_idempotent(self, service, session_factory):
        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)

        first = await service.purge_request(request_id=request.id)
        assert first.status == DeletionRequestStatus.PURGED

        # Second call is a no-op: user_id has already been severed.
        second = await service.purge_request(request_id=request.id)
        assert second.status == DeletionRequestStatus.PURGED

    async def test_purge_report_records_every_handler(
        self, service, session_factory
    ):
        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)

        result = await service.purge_request(request_id=request.id)

        report = result.purge_report
        assert report["ok"] is True
        names = {h["handler"] for h in report["handlers"]}
        assert "identity" in names
        assert "cloudinary_objects" in names

    async def test_purge_report_contains_no_personal_data(
        self, service, session_factory
    ):
        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)

        result = await service.purge_request(request_id=request.id)

        serialised = str(result.purge_report)
        assert user.phone not in serialised
        assert user.email not in serialised
        assert "Test Person" not in serialised

    async def test_cancelled_request_cannot_be_purged(
        self, service, session_factory
    ):
        from app.services.exceptions import ValidationError

        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)
        await service.cancel_deletion(user_id=user.id)

        with pytest.raises(ValidationError):
            await service.purge_request(request_id=request.id)

    async def test_missing_request_raises_not_found(self, service):
        from app.services.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            await service.purge_request(request_id=uuid.uuid4())

    async def test_run_due_summarises_the_batch(self, service, session_factory):
        for _ in range(3):
            user = await _make_user(session_factory)
            await service.request_deletion(user_id=user.id)

        future = datetime.now(tz=timezone.utc) + timedelta(days=15)
        summary = await service.run_due(now=future)

        assert summary["due"] == 3
        assert summary["purged"] == 3
        assert summary["incomplete"] == 0
        assert summary["failed"] == 0

    async def test_run_due_ignores_active_users(self, service, session_factory):
        """An account that never asked to be deleted is never touched."""
        await _make_user(session_factory)

        far_future = datetime.now(tz=timezone.utc) + timedelta(days=3650)
        summary = await service.run_due(now=far_future)

        assert summary["due"] == 0


class TestStorageHonesty:
    """The pipeline must never claim a deletion it did not perform."""

    async def test_unreachable_storage_yields_incomplete(
        self, service, session_factory, monkeypatch
    ):
        from app.services.deletion.handlers import external

        async def _fail(public_id: str, *, resource_type: str = "image") -> bool:
            return False

        monkeypatch.setattr(external.cloudinary_client, "destroy_asset", _fail)

        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)
        result = await service.purge_request(request_id=request.id)

        assert result.status == DeletionRequestStatus.INCOMPLETE, (
            "a storage object that could not be destroyed must not be reported "
            "as a completed purge"
        )
        assert result.user_id is not None, (
            "an incomplete purge must keep its subject reference so it can be retried"
        )

    async def test_incomplete_can_be_retried_to_completion(
        self, service, session_factory, monkeypatch
    ):
        from app.services.deletion.handlers import external

        async def _fail(public_id: str, *, resource_type: str = "image") -> bool:
            return False

        monkeypatch.setattr(external.cloudinary_client, "destroy_asset", _fail)

        user = await _make_user(session_factory)
        request = await service.request_deletion(user_id=user.id)
        first = await service.purge_request(request_id=request.id)
        assert first.status == DeletionRequestStatus.INCOMPLETE

        # Storage comes back; the operator clears the unresolved markers and
        # the same request is retried.
        async def _ok(public_id: str, *, resource_type: str = "image") -> bool:
            return True

        monkeypatch.setattr(external.cloudinary_client, "destroy_asset", _ok)
        async with session_factory() as s:
            from sqlalchemy import text

            await s.execute(text("DELETE FROM unresolved_media_assets"))
            await s.commit()

        second = await service.purge_request(request_id=request.id)
        assert second.status == DeletionRequestStatus.PURGED
        assert second.user_id is None
