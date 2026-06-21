"""
Base service infrastructure for all Tyohaar domain services.

Pattern:
    class FooService(BaseService):
        async def do_something(self, data: FooCreate) -> FooResponse:
            async with self._uow() as uow:
                foo = await uow.foos.foos.create(data.model_dump())
                return FooResponse.model_validate(foo)

All services receive a `session_factory` in their constructor so that tests
can inject a fixture session without hitting the real database.

Cross-domain DB operations share the same UoW context (single transaction):
    async with self._uow() as uow:
        booking = await uow.bookings.bookings.create(...)
        await uow.wallets.transactions.create(...)   # same tx

Side effects that must NOT roll back with the transaction (e.g. SMS, push)
are executed AFTER the `async with` block exits successfully.
"""

from __future__ import annotations

from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.repositories.unit_of_work import UnitOfWork


class BaseService:
    """
    Abstract base for all Tyohaar domain services.

    Subclasses MUST NOT hold a long-lived UoW or session reference.
    Create a new UoW per business operation to keep transactions atomic.
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    ) -> None:
        self._session_factory = session_factory

    def _uow(self) -> UnitOfWork:
        """Return a new UnitOfWork bound to this service's session factory."""
        return UnitOfWork(self._session_factory)
