"""
Booking repository — Booking and all booking-domain child models.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bookings.booking import Booking
from app.models.bookings.booking_assignment import BookingAssignment
from app.models.bookings.booking_cancellation import BookingCancellation
from app.models.bookings.booking_history import BookingHistory, BookingEventType, BookingActorType
from app.models.bookings.booking_invoice import BookingInvoice
from app.models.bookings.booking_item import BookingItem
from app.models.bookings.booking_reschedule import BookingReschedule
from app.models.bookings.booking_status import BookingStatusRecord
from app.models.bookings.booking_status_history import BookingStatusHistory
from app.models.enums import BookingStatus, PaymentStatus
from app.repositories.base import BaseRepository, NotFoundError


class BookingRepository(BaseRepository[Booking]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Booking)

    async def find_by_number(self, booking_number: str) -> Booking | None:
        return await self.find_one(Booking.booking_number == booking_number)

    async def find_by_customer(
        self,
        customer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Booking]:
        return await self.find_many(
            Booking.customer_id == customer_id,
            order_by=Booking.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_celebration(self, celebration_id: uuid.UUID) -> list[Booking]:
        return await self.find_many(Booking.celebration_id == celebration_id)

    async def find_by_status(
        self,
        status: BookingStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        return await self.find_many(
            Booking.booking_status == status,
            skip=skip,
            limit=limit,
        )

    async def find_upcoming_for_customer(
        self,
        customer_id: uuid.UUID,
        after: date,
    ) -> list[Booking]:
        return await self.find_many(
            Booking.customer_id == customer_id,
            Booking.scheduled_date > after,
            Booking.booking_status.in_([
                BookingStatus.CONFIRMED,
                BookingStatus.IN_PROGRESS,
            ]),
            order_by=Booking.scheduled_date.asc(),
        )

    async def find_completed_for_customer(
        self,
        customer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Booking]:
        return await self.find_many(
            Booking.customer_id == customer_id,
            Booking.booking_status == BookingStatus.COMPLETED,
            order_by=Booking.scheduled_date.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_scheduled_for_date(self, on_date: date) -> list[Booking]:
        return await self.find_many(
            Booking.scheduled_date == on_date,
            Booking.booking_status == BookingStatus.CONFIRMED,
        )

    async def find_requiring_assignment(self) -> list[Booking]:
        """Return CONFIRMED bookings that have no accepted vendor assignments yet."""
        from sqlalchemy import exists
        sub = (
            select(BookingAssignment.id)
            .join(BookingItem, BookingItem.id == BookingAssignment.booking_item_id)
            .where(BookingItem.booking_id == Booking.id)
            .where(BookingAssignment.assignment_status == "accepted")
            .correlate(Booking)
        )
        stmt = (
            self._base_select()
            .where(Booking.booking_status == BookingStatus.CONFIRMED)
            .where(~exists(sub))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_payment_status(
        self,
        payment_status: PaymentStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        return await self.find_many(
            Booking.payment_status == payment_status,
            skip=skip,
            limit=limit,
        )

    async def get_with_items(self, booking_id: uuid.UUID) -> Booking | None:
        return await self.get_by_id(
            booking_id,
            options=[selectinload(Booking.items)],
        )

    async def get_with_assignments(self, booking_id: uuid.UUID) -> Booking | None:
        return await self.get_by_id(
            booking_id,
            options=[
                selectinload(Booking.items).selectinload(BookingItem.assignments),
            ],
        )

    async def get_full(self, booking_id: uuid.UUID) -> Booking | None:
        return await self.get_by_id(
            booking_id,
            options=[
                selectinload(Booking.items),
                selectinload(Booking.status_history),
                selectinload(Booking.invoices),
            ],
        )

    async def count_by_status(self) -> dict[str, int]:
        stmt = (
            select(Booking.booking_status, func.count().label("count"))
            .where(Booking.deleted_at.is_(None))
            .group_by(Booking.booking_status)
        )
        result = await self._session.execute(stmt)
        return {str(row.booking_status): row.count for row in result.all()}


class BookingItemRepository(BaseRepository[BookingItem]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BookingItem)

    async def find_by_booking(self, booking_id: uuid.UUID) -> list[BookingItem]:
        return await self.find_many(BookingItem.booking_id == booking_id)

    async def find_by_package_item(self, package_item_id: uuid.UUID) -> list[BookingItem]:
        return await self.find_many(BookingItem.package_item_id == package_item_id)


class BookingAssignmentRepository(BaseRepository[BookingAssignment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BookingAssignment)

    async def find_by_booking_item(self, booking_item_id: uuid.UUID) -> list[BookingAssignment]:
        return await self.find_many(BookingAssignment.booking_item_id == booking_item_id)

    async def find_by_vendor(
        self,
        vendor_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[BookingAssignment]:
        return await self.find_many(
            BookingAssignment.vendor_id == vendor_id,
            order_by=BookingAssignment.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_active_for_vendor(self, vendor_id: uuid.UUID) -> list[BookingAssignment]:
        return await self.find_many(
            BookingAssignment.vendor_id == vendor_id,
            BookingAssignment.assignment_status == "accepted",
        )

    async def count_for_vendor(self, vendor_id: uuid.UUID) -> int:
        return await self.count(BookingAssignment.vendor_id == vendor_id)


class BookingStatusHistoryRepository(BaseRepository[BookingStatusHistory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BookingStatusHistory)

    async def find_by_booking(self, booking_id: uuid.UUID) -> list[BookingStatusHistory]:
        return await self.find_many(
            BookingStatusHistory.booking_id == booking_id,
            order_by=BookingStatusHistory.created_at.asc(),
        )


class BookingCancellationRepository(BaseRepository[BookingCancellation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BookingCancellation)

    async def find_by_booking(self, booking_id: uuid.UUID) -> BookingCancellation | None:
        return await self.find_one(BookingCancellation.booking_id == booking_id)


class BookingRescheduleRepository(BaseRepository[BookingReschedule]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BookingReschedule)

    async def find_by_booking(self, booking_id: uuid.UUID) -> list[BookingReschedule]:
        return await self.find_many(
            BookingReschedule.booking_id == booking_id,
            order_by=BookingReschedule.created_at.desc(),
        )

    async def count_for_booking(self, booking_id: uuid.UUID) -> int:
        return await self.count(BookingReschedule.booking_id == booking_id)


class BookingInvoiceRepository(BaseRepository[BookingInvoice]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BookingInvoice)

    async def find_by_booking(self, booking_id: uuid.UUID) -> BookingInvoice | None:
        return await self.find_one(BookingInvoice.booking_id == booking_id)

    async def find_by_number(self, invoice_number: str) -> BookingInvoice | None:
        return await self.find_one(BookingInvoice.invoice_number == invoice_number)


class BookingHistoryRepository(BaseRepository[BookingHistory]):
    """
    IMMUTABLE: only create() is permitted. Rows are the authoritative audit log.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BookingHistory)

    async def update(self, instance: BookingHistory, data: dict) -> BookingHistory:  # type: ignore[override]
        from app.repositories.base import RepositoryError
        raise RepositoryError("BookingHistory is immutable — updates are not permitted.")

    async def delete(self, instance: BookingHistory) -> None:  # type: ignore[override]
        from app.repositories.base import RepositoryError
        raise RepositoryError("BookingHistory is immutable — deletes are not permitted.")

    async def soft_delete(self, instance: BookingHistory) -> None:  # type: ignore[override]
        from app.repositories.base import RepositoryError
        raise RepositoryError("BookingHistory is immutable — soft deletes are not permitted.")

    # ── Queries ───────────────────────────────────────────────────────────────

    async def find_by_booking(
        self,
        booking_id: uuid.UUID,
        *,
        include_internal: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BookingHistory]:
        filters: list[Any] = [BookingHistory.booking_id == booking_id]
        if not include_internal:
            filters.append(BookingHistory.is_customer_visible == True)  # noqa: E712
        return await self.find_many(
            *filters,
            order_by=BookingHistory.occurred_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_visible_for_customer(
        self,
        booking_id: uuid.UUID,
    ) -> list[BookingHistory]:
        return await self.find_many(
            BookingHistory.booking_id == booking_id,
            BookingHistory.is_customer_visible == True,  # noqa: E712
            order_by=BookingHistory.occurred_at.asc(),
        )

    async def find_by_event_type(
        self,
        booking_id: uuid.UUID,
        event_type: BookingEventType,
    ) -> list[BookingHistory]:
        return await self.find_many(
            BookingHistory.booking_id == booking_id,
            BookingHistory.event_type == event_type,
            order_by=BookingHistory.occurred_at.asc(),
        )

    async def find_by_actor(
        self,
        actor_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[BookingHistory]:
        return await self.find_many(
            BookingHistory.actor_id == actor_id,
            order_by=BookingHistory.occurred_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_actor_type(
        self,
        booking_id: uuid.UUID,
        actor_type: BookingActorType,
    ) -> list[BookingHistory]:
        return await self.find_many(
            BookingHistory.booking_id == booking_id,
            BookingHistory.actor_type == actor_type,
            order_by=BookingHistory.occurred_at.asc(),
        )

    async def find_in_range(
        self,
        start: datetime,
        end: datetime,
        *,
        skip: int = 0,
        limit: int = 200,
    ) -> list[BookingHistory]:
        return await self.find_many(
            BookingHistory.occurred_at >= start,
            BookingHistory.occurred_at <= end,
            order_by=BookingHistory.occurred_at.asc(),
            skip=skip,
            limit=limit,
        )


class BookingStatusRecordRepository(BaseRepository[BookingStatusRecord]):
    """
    One record per booking — the live SLA/analytics snapshot.
    Upserted by the service layer on every status transition.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BookingStatusRecord)

    async def get_by_booking(self, booking_id: uuid.UUID) -> BookingStatusRecord | None:
        return await self.find_one(BookingStatusRecord.booking_id == booking_id)

    async def get_by_booking_or_raise(self, booking_id: uuid.UUID) -> BookingStatusRecord:
        record = await self.get_by_booking(booking_id)
        if record is None:
            raise NotFoundError("BookingStatusRecord", f"booking_id={booking_id}")
        return record

    async def get_by_booking_with_lock(
        self,
        booking_id: uuid.UUID,
    ) -> BookingStatusRecord | None:
        """SELECT FOR UPDATE — used by the service layer during status transitions."""
        stmt = (
            select(BookingStatusRecord)
            .where(BookingStatusRecord.booking_id == booking_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_sla_breached(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BookingStatusRecord]:
        return await self.find_many(
            BookingStatusRecord.sla_breached == True,  # noqa: E712
            order_by=BookingStatusRecord.sla_breached_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_sla_at_risk(self) -> list[BookingStatusRecord]:
        """Records where the SLA deadline is approaching but not yet breached."""
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            BookingStatusRecord.sla_deadline_at.is_not(None),
            BookingStatusRecord.sla_deadline_at <= now,
            BookingStatusRecord.sla_breached == False,  # noqa: E712
        )

    async def find_requiring_action(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BookingStatusRecord]:
        return await self.find_many(
            BookingStatusRecord.requires_action == True,  # noqa: E712
            order_by=BookingStatusRecord.updated_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_assigned_to(
        self,
        admin_id: uuid.UUID,
    ) -> list[BookingStatusRecord]:
        return await self.find_many(
            BookingStatusRecord.assigned_to_id == admin_id,
            BookingStatusRecord.requires_action == True,  # noqa: E712
            order_by=BookingStatusRecord.sla_deadline_at.asc(),
        )

    async def find_by_status(
        self,
        status: BookingStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BookingStatusRecord]:
        return await self.find_many(
            BookingStatusRecord.current_status == status,
            order_by=BookingStatusRecord.status_entered_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def mark_sla_breached(
        self,
        booking_id: uuid.UUID,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(BookingStatusRecord)
            .where(BookingStatusRecord.booking_id == booking_id)
            .where(BookingStatusRecord.sla_breached == False)  # noqa: E712
            .values(sla_breached=True, sla_breached_at=now)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)


class BookingRepositoryAggregate:
    """Groups all booking-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.bookings = BookingRepository(session)
        self.items = BookingItemRepository(session)
        self.assignments = BookingAssignmentRepository(session)
        self.status_history = BookingStatusHistoryRepository(session)
        self.history = BookingHistoryRepository(session)
        self.status_records = BookingStatusRecordRepository(session)
        self.cancellations = BookingCancellationRepository(session)
        self.reschedules = BookingRescheduleRepository(session)
        self.invoices = BookingInvoiceRepository(session)
