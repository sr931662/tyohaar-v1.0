"""
Generic async SQLAlchemy 2.0 repository base.

All domain repositories inherit from BaseRepository[ModelT] and share one
AsyncSession instance per request/unit-of-work. Business logic is strictly
forbidden here — repositories only move data between Python and the database.
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


# ── Exceptions ────────────────────────────────────────────────────────────────


class RepositoryError(Exception):
    """Base class for all repository-layer exceptions."""


class NotFoundError(RepositoryError):
    """Raised when a required entity does not exist."""

    def __init__(self, model: str, identifier: Any) -> None:
        super().__init__(f"{model} not found: {identifier!r}")
        self.model = model
        self.identifier = identifier


class AlreadyExistsError(RepositoryError):
    """Raised on unique-constraint violations caught before flush."""

    def __init__(self, model: str, field: str, value: Any) -> None:
        super().__init__(f"{model}.{field} already exists: {value!r}")
        self.model = model
        self.field = field
        self.value = value


class StaleDataError(RepositoryError):
    """Raised when an optimistic concurrency check fails."""


class DatabaseError(RepositoryError):
    """Wraps unexpected SQLAlchemy or database errors."""


# ── Pagination ────────────────────────────────────────────────────────────────


@dataclass
class Page(Generic[ModelT]):
    items: list[ModelT]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        if self.page_size == 0:
            return 0
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


@dataclass
class CursorPage(Generic[ModelT]):
    """Result page for cursor-based (keyset) pagination.

    Cursor encodes (created_at ISO string, id UUID string) of the last item
    in the current page. Pass it as ``cursor`` on the next call to retrieve
    the subsequent page.  ``next_cursor`` is None when there are no more rows.
    """

    items: list[ModelT]
    next_cursor: str | None
    page_size: int

    @property
    def has_next(self) -> bool:
        return self.next_cursor is not None


def _encode_cursor(created_at: datetime, id: uuid.UUID) -> str:
    payload = {"ts": created_at.isoformat(), "id": str(id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(data["ts"]), uuid.UUID(data["id"])
    except Exception as exc:
        raise RepositoryError(f"Invalid cursor: {cursor!r}") from exc


# ── Base Repository ───────────────────────────────────────────────────────────


class BaseRepository(Generic[ModelT]):
    """
    Generic async repository for SQLAlchemy 2.0 declarative models.

    Every subclass receives the SAME AsyncSession instance, which means all
    repositories within a single UnitOfWork participate in one transaction.

    Soft-delete detection: if the model has a `deleted_at` column, queries
    automatically exclude soft-deleted rows unless `include_deleted=True`.
    """

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model
        self._has_soft_delete: bool = hasattr(model, "deleted_at")

    # ── Session Helpers ───────────────────────────────────────────────────────

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def flush(self) -> None:
        await self._session.flush()

    async def refresh(self, instance: ModelT) -> None:
        await self._session.refresh(instance)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _base_select(self, include_deleted: bool = False) -> Select:
        stmt = select(self._model)
        if self._has_soft_delete and not include_deleted:
            stmt = stmt.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    def _apply_ordering(self, stmt: Select, order_by: Any) -> Select:
        if order_by is None:
            return stmt
        if isinstance(order_by, (list, tuple)):
            return stmt.order_by(*order_by)
        return stmt.order_by(order_by)

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        id: uuid.UUID,
        *,
        options: Sequence[Any] = (),
        include_deleted: bool = False,
    ) -> ModelT | None:
        stmt = self._base_select(include_deleted).where(self._model.id == id)  # type: ignore[attr-defined]
        if options:
            stmt = stmt.options(*options)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(
        self,
        id: uuid.UUID,
        *,
        options: Sequence[Any] = (),
        include_deleted: bool = False,
    ) -> ModelT:
        instance = await self.get_by_id(id, options=options, include_deleted=include_deleted)
        if instance is None:
            raise NotFoundError(self._model.__name__, id)
        return instance

    async def get_by_id_with_lock(
        self,
        id: uuid.UUID,
        *,
        skip_locked: bool = False,
        include_deleted: bool = False,
    ) -> ModelT | None:
        """SELECT FOR UPDATE — acquires a pessimistic row-level lock."""
        stmt = (
            self._base_select(include_deleted)
            .where(self._model.id == id)  # type: ignore[attr-defined]
            .with_for_update(skip_locked=skip_locked)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(
        self,
        ids: list[uuid.UUID],
        *,
        options: Sequence[Any] = (),
        include_deleted: bool = False,
    ) -> list[ModelT]:
        if not ids:
            return []
        stmt = (
            self._base_select(include_deleted)
            .where(self._model.id.in_(ids))  # type: ignore[attr-defined]
        )
        if options:
            stmt = stmt.options(*options)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_one(
        self,
        *filters: Any,
        options: Sequence[Any] = (),
        include_deleted: bool = False,
    ) -> ModelT | None:
        stmt = self._base_select(include_deleted)
        if filters:
            stmt = stmt.where(*filters)
        if options:
            stmt = stmt.options(*options)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_many(
        self,
        *filters: Any,
        options: Sequence[Any] = (),
        order_by: Any = None,
        skip: int = 0,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        stmt = self._base_select(include_deleted)
        if filters:
            stmt = stmt.where(*filters)
        if options:
            stmt = stmt.options(*options)
        stmt = self._apply_ordering(stmt, order_by)
        if skip:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Any = None,
        options: Sequence[Any] = (),
        include_deleted: bool = False,
    ) -> list[ModelT]:
        stmt = self._base_select(include_deleted)
        if options:
            stmt = stmt.options(*options)
        stmt = self._apply_ordering(stmt, order_by)
        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def exists(self, id: uuid.UUID, *, include_deleted: bool = False) -> bool:
        stmt = select(func.count()).select_from(self._model)
        stmt = stmt.where(self._model.id == id)  # type: ignore[attr-defined]
        if self._has_soft_delete and not include_deleted:
            stmt = stmt.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def exists_where(self, *filters: Any) -> bool:
        """Return True if any row matches the given filters."""
        stmt = select(func.count()).select_from(self._model).where(*filters)
        if self._has_soft_delete:
            stmt = stmt.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def count(
        self,
        *filters: Any,
        include_deleted: bool = False,
    ) -> int:
        stmt = select(func.count()).select_from(self._model)
        if self._has_soft_delete and not include_deleted:
            stmt = stmt.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
        if filters:
            stmt = stmt.where(*filters)
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(self, instance: ModelT) -> ModelT:
        try:
            self._session.add(instance)
            await self._session.flush()
            await self._session.refresh(instance)
            return instance
        except Exception as exc:
            raise DatabaseError(f"Create {self._model.__name__} failed: {exc}") from exc

    async def create_from_dict(self, data: dict[str, Any]) -> ModelT:
        return await self.create(self._model(**data))

    async def update(self, instance: ModelT, data: dict[str, Any]) -> ModelT:
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        try:
            await self._session.flush()
            await self._session.refresh(instance)
            return instance
        except Exception as exc:
            raise DatabaseError(f"Update {self._model.__name__} failed: {exc}") from exc

    async def delete(self, instance: ModelT) -> None:
        """Hard delete. Prefer soft_delete() for auditable models."""
        await self._session.delete(instance)
        await self._session.flush()

    async def soft_delete(self, instance: ModelT) -> None:
        if not self._has_soft_delete:
            raise RepositoryError(f"{self._model.__name__} does not support soft delete.")
        instance.deleted_at = datetime.now(tz=timezone.utc)  # type: ignore[attr-defined]
        await self._session.flush()

    async def restore(self, instance: ModelT) -> ModelT:
        if not self._has_soft_delete:
            raise RepositoryError(f"{self._model.__name__} does not support restore.")
        instance.deleted_at = None  # type: ignore[attr-defined]
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    # ── Bulk ──────────────────────────────────────────────────────────────────

    async def bulk_create(self, instances: list[ModelT]) -> list[ModelT]:
        if not instances:
            return []
        try:
            self._session.add_all(instances)
            await self._session.flush()
            return instances
        except Exception as exc:
            raise DatabaseError(f"Bulk create {self._model.__name__} failed: {exc}") from exc

    async def bulk_update(
        self,
        ids: list[uuid.UUID],
        data: dict[str, Any],
    ) -> int:
        if not ids:
            return 0
        stmt = (
            update(self._model)
            .where(self._model.id.in_(ids))  # type: ignore[attr-defined]
            .values(**data)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def bulk_delete(self, ids: list[uuid.UUID]) -> int:
        if not ids:
            return 0
        stmt = (
            delete(self._model)
            .where(self._model.id.in_(ids))  # type: ignore[attr-defined]
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def bulk_soft_delete(self, ids: list[uuid.UUID]) -> int:
        if not self._has_soft_delete:
            raise RepositoryError(f"{self._model.__name__} does not support soft delete.")
        if not ids:
            return 0
        stmt = (
            update(self._model)
            .where(self._model.id.in_(ids))  # type: ignore[attr-defined]
            .where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
            .values(deleted_at=datetime.now(tz=timezone.utc))
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    # ── Pagination ────────────────────────────────────────────────────────────

    async def paginate(
        self,
        *filters: Any,
        page: int = 1,
        page_size: int = 20,
        order_by: Any = None,
        options: Sequence[Any] = (),
        include_deleted: bool = False,
    ) -> Page[ModelT]:
        page = max(1, page)
        page_size = max(1, min(page_size, 200))
        skip = (page - 1) * page_size

        count_stmt = select(func.count()).select_from(self._model)
        if self._has_soft_delete and not include_deleted:
            count_stmt = count_stmt.where(self._model.deleted_at.is_(None))  # type: ignore[attr-defined]
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await self._session.execute(count_stmt)).scalar_one() or 0

        stmt = self._base_select(include_deleted)
        if filters:
            stmt = stmt.where(*filters)
        if options:
            stmt = stmt.options(*options)
        stmt = self._apply_ordering(stmt, order_by)
        stmt = stmt.offset(skip).limit(page_size)
        items = list((await self._session.execute(stmt)).scalars().all())

        return Page(items=items, total=total, page=page, page_size=page_size)

    async def cursor_paginate(
        self,
        *filters: Any,
        cursor: str | None = None,
        limit: int = 20,
        options: Sequence[Any] = (),
        include_deleted: bool = False,
    ) -> CursorPage[ModelT]:
        """Keyset (cursor) pagination ordered by (created_at DESC, id DESC).

        The model must have ``created_at`` (TimestampMixin) and ``id``
        (UUIDPrimaryKeyMixin) columns.  Pass the returned ``next_cursor`` as
        ``cursor`` on the next call to get the following page.
        """
        limit = max(1, min(limit, 200))
        stmt = self._base_select(include_deleted)

        if filters:
            stmt = stmt.where(*filters)

        if cursor is not None:
            cursor_ts, cursor_id = _decode_cursor(cursor)
            stmt = stmt.where(
                (self._model.created_at < cursor_ts)  # type: ignore[attr-defined]
                | (
                    (self._model.created_at == cursor_ts)  # type: ignore[attr-defined]
                    & (self._model.id < cursor_id)  # type: ignore[attr-defined]
                )
            )

        if options:
            stmt = stmt.options(*options)

        stmt = stmt.order_by(
            self._model.created_at.desc(),  # type: ignore[attr-defined]
            self._model.id.desc(),  # type: ignore[attr-defined]
        ).limit(limit + 1)

        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = _encode_cursor(
                last.created_at,  # type: ignore[attr-defined]
                last.id,  # type: ignore[attr-defined]
            )

        return CursorPage(items=items, next_cursor=next_cursor, page_size=limit)

    # ── Raw Execution ─────────────────────────────────────────────────────────

    async def execute(self, stmt: Any) -> Any:
        """Execute an arbitrary SQLAlchemy statement and return the raw result."""
        return await self._session.execute(stmt)
