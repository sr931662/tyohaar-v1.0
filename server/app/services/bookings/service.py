from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.models.bookings.booking import Booking
from app.models.bookings.booking_assignment import BookingAssignment
from app.models.bookings.booking_cancellation import BookingCancellation
from app.models.bookings.booking_history import BookingActorType, BookingEventType, BookingHistory
from app.models.bookings.booking_invoice import BookingInvoice
from app.models.bookings.booking_item import BookingItem
from app.models.bookings.booking_reschedule import BookingReschedule, RescheduleStatus
from app.models.bookings.booking_status_history import BookingStatusHistory
from app.models.enums import AssignmentStatus, BookingStatus, InvoiceStatus, PaymentStatus
from app.schemas.base import CursorPage
from app.schemas.bookings import (
    BookingAssignmentInternal,
    BookingCancellationCreate,
    BookingCancellationResponse,
    BookingCreate,
    BookingDetailResponse,
    BookingFilters,
    BookingInvoiceResponse,
    BookingResponse,
    BookingRescheduleCreate,
    BookingRescheduleResponse,
    BookingStatusHistoryResponse,
)
from app.services.base import BaseService
from app.services.bookings.constants import (
    CANCELLATION_FEE_PERCENTAGE,
    CANCELLATION_WINDOW_HOURS,
)
from app.services.bookings.exceptions import (
    AssignmentNotFoundError,
    BookingNotFoundError,
    BookingOwnershipError,
    BookingStatusTransitionError,
    CelebrationRequiredError,
    VendorNotAvailableError,
)
from app.services.bookings.helpers import (
    calculate_booking_total,
    calculate_cancellation_fee,
    calculate_refund_amount,
    generate_booking_reference,
)
from app.services.bookings.validators import (
    validate_booking_cutoff,
    validate_booking_exists,
    validate_booking_ownership,
    validate_cancellation_window,
    validate_package_available,
    validate_reschedule_window,
    validate_status_transition_allowed,
    validate_vendor_availability_for_booking,
)


class BookingService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _scheduled_event_dt(self, data: BookingCreate) -> datetime:
        t = data.scheduled_start_time or time(0, 0, 0)
        d = data.scheduled_date
        return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=timezone.utc)

    async def _write_history_event(
        self,
        uow,
        booking_id: UUID,
        event_type: BookingEventType,
        actor_type: BookingActorType,
        actor_id: UUID | None,
        event_label: str | None = None,
        description: str | None = None,
        is_customer_visible: bool = True,
        context_data: dict | None = None,
    ) -> None:
        entry = BookingHistory(
            booking_id=booking_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            event_label=event_label,
            description=description,
            is_customer_visible=is_customer_visible,
            occurred_at=datetime.now(tz=timezone.utc),
            context_data=context_data,
        )
        await uow.bookings.history.create(entry)

    async def _write_status_history(
        self,
        uow,
        booking_id: UUID,
        old_status: BookingStatus | None,
        new_status: BookingStatus,
        changed_by_id: UUID | None,
        reason: str | None = None,
    ) -> None:
        record = BookingStatusHistory(
            booking_id=booking_id,
            old_status=old_status,
            new_status=new_status,
            changed_by_id=changed_by_id,
            transitioned_at=datetime.now(tz=timezone.utc),
            reason=reason,
        )
        await uow.bookings.status_history.create(record)

    # ── Core booking lifecycle ────────────────────────────────────────────────

    async def create_booking(
        self,
        customer_id: UUID,
        data: BookingCreate,
    ) -> BookingResponse:
        event_dt = self._scheduled_event_dt(data)
        validate_booking_cutoff(event_dt)

        async with self._uow() as uow:
            # Validate package exists and is available
            package = await validate_package_available(data.package_id, data.scheduled_date, uow)

            celebration_id = data.celebration_id
            if celebration_id is None:
                occasion_id = data.occasion_id
                if occasion_id is None:
                    from sqlalchemy import select

                    from app.models.packages.package import package_occasions

                    result = await uow.session.execute(
                        select(package_occasions.c.occasion_id)
                        .where(package_occasions.c.package_id == data.package_id)
                        .limit(1)
                    )
                    occasion_id = result.scalar_one_or_none()

                if occasion_id is None:
                    raise CelebrationRequiredError()

                celebration = await uow.occasions.celebrations.create_from_dict({
                    "customer_id": customer_id,
                    "occasion_id": occasion_id,
                    "title": data.celebration_title or f"{package.name} booking",
                    "celebration_date": data.scheduled_date,
                    "venue_address": data.venue_address,
                    "theme_id": data.theme_id,
                    "guest_count": 0,
                })
                celebration_id = celebration.id

            # 1. Fetch mandatory items from package
            package_items = await uow.packages.items.find_by_package(data.package_id)
            selected_items = [i for i in package_items if i.is_mandatory]

            # 2. Fetch selected optional items (add-ons)
            if data.item_ids:
                optional_items = [i for i in package_items if not i.is_mandatory and i.id in data.item_ids]
                selected_items.extend(optional_items)

            # 3. Calculate financials — package base price + selected items.
            # Package.base_price is the package's own starting price; item
            # rows are line-item add-ons/inclusions on top of it, not a
            # replacement for it (previously this only summed items, so a
            # package with no items priced the booking at ₹0 subtotal).
            items_total = sum((i.base_price * i.quantity) for i in selected_items)
            subtotal = (package.base_price or Decimal("0.00")) + items_total
            platform_fee = Decimal("0.00")  # Platform fee removed project-wide.
            tax_rate = Decimal("0.18")
            tax_amount = (subtotal * tax_rate).quantize(Decimal("0.01"))
            total_amount = subtotal + tax_amount + platform_fee

            booking_ref = generate_booking_reference()

            booking = Booking(
                booking_number=booking_ref,
                customer_id=customer_id,
                celebration_id=celebration_id,
                package_id=data.package_id,
                address_id=data.address_id,
                recipient_name=data.recipient_name,
                recipient_phone=data.recipient_phone,
                scheduled_date=data.scheduled_date,
                scheduled_start_time=data.scheduled_start_time,
                scheduled_end_time=data.scheduled_end_time,
                booking_type=data.booking_type,
                booking_status=BookingStatus.PENDING,
                payment_status=PaymentStatus.PENDING,
                currency=data.currency,
                subtotal=subtotal,
                discount_amount=Decimal("0.00"),
                tax_amount=tax_amount,
                platform_fee=platform_fee,
                total_amount=total_amount,
                amount_paid=Decimal("0.00"),
                amount_due=total_amount,
                special_instructions=data.special_instructions,
            )
            booking = await uow.bookings.bookings.create(booking)

            # 4. Create BookingItem records
            for idx, pi in enumerate(selected_items):
                item = BookingItem(
                    booking_id=booking.id,
                    package_item_id=pi.id,
                    name=pi.name,
                    description=pi.description,
                    quantity=pi.quantity,
                    unit=pi.unit,
                    unit_price=pi.base_price,
                    final_price=pi.base_price * pi.quantity,
                    is_mandatory=pi.is_mandatory,
                    is_addon=not pi.is_mandatory,
                    display_order=idx,
                )
                await uow.bookings.items.create(item)

            # Write status and history
            await self._write_status_history(
                uow, booking.id, None, BookingStatus.PENDING, customer_id, "Booking created"
            )
            await self._write_history_event(
                uow,
                booking_id=booking.id,
                event_type=BookingEventType.STATUS_CHANGED,
                actor_type=BookingActorType.CUSTOMER,
                actor_id=customer_id,
                event_label="Booking submitted",
                description=f"Booking for {package.name} created.",
            )

            await uow.commit()
            return BookingResponse.model_validate(booking)

    async def get_booking(
        self,
        booking_id: UUID,
        requester_id: UUID,
        requester_role: str,
    ) -> BookingDetailResponse:
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)

            # Access control: customers can only see their own bookings
            if requester_role == "customer" and booking.customer_id != requester_id:
                raise BookingOwnershipError(
                    f"Booking {booking_id} does not belong to customer {requester_id}."
                )
            # Vendors: they access through list_vendor_bookings; detail access here is permissive
            # Admin / support: unrestricted

            return BookingDetailResponse.model_validate(booking)

    async def list_bookings(
        self,
        customer_id: UUID | None,
        filters: BookingFilters,
        cursor: str | None,
        limit: int,
    ) -> CursorPage[BookingResponse]:
        async with self._uow() as uow:
            conditions = []
            if customer_id is not None:
                conditions.append(uow.bookings.bookings._model.customer_id == customer_id)
            page = await uow.bookings.bookings.cursor_paginate(
                *conditions,
                cursor=cursor,
                limit=limit,
            )
            items = [BookingResponse.model_validate(b) for b in page.items]
            return CursorPage(
                items=items,
                next_cursor=page.next_cursor,
                has_more=page.has_next,
            )

    async def list_vendor_bookings(
        self,
        vendor_id: UUID,
        filters: BookingFilters,
        cursor: str | None,
        limit: int,
    ) -> CursorPage[BookingResponse]:
        async with self._uow() as uow:
            # Derive bookings assigned to this vendor via assignments
            assignments = await uow.bookings.assignments.find_by_vendor(vendor_id, limit=1000)
            booking_ids = list({a.booking_id for a in assignments})
            if not booking_ids:
                return CursorPage(items=[], next_cursor=None, has_more=False)

            page = await uow.bookings.bookings.cursor_paginate(
                uow.bookings.bookings._model.id.in_(booking_ids),
                cursor=cursor,
                limit=limit,
            )
            items = [BookingResponse.model_validate(b) for b in page.items]
            return CursorPage(
                items=items,
                next_cursor=page.next_cursor,
                has_more=page.has_next,
            )

    # ── Status transitions ────────────────────────────────────────────────────

    async def confirm_booking(
        self,
        booking_id: UUID,
        admin_id: UUID,
    ) -> BookingResponse:
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)
            validate_status_transition_allowed(booking, "confirmed")
            old_status = booking.booking_status

            booking = await uow.bookings.bookings.update(
                booking,
                {
                    "booking_status": BookingStatus.CONFIRMED,
                    "confirmed_at": datetime.now(tz=timezone.utc),
                },
            )

            await self._write_status_history(
                uow, booking.id, old_status, BookingStatus.CONFIRMED, admin_id
            )
            await self._write_history_event(
                uow,
                booking_id=booking.id,
                event_type=BookingEventType.STATUS_CHANGED,
                actor_type=BookingActorType.ADMIN,
                actor_id=admin_id,
                event_label="Booking confirmed",
                context_data={"new_status": BookingStatus.CONFIRMED.value},
            )

            await uow.commit()
            return BookingResponse.model_validate(booking)

    async def start_booking(
        self,
        booking_id: UUID,
        vendor_id: UUID,
    ) -> BookingResponse:
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)
            validate_status_transition_allowed(booking, "in_progress")

            # Validate vendor has an accepted assignment on this booking
            assignments = await uow.bookings.assignments.find_many(
                uow.bookings.assignments._model.booking_id == booking_id,
                uow.bookings.assignments._model.vendor_id == vendor_id,
            )
            if not assignments:
                raise VendorNotAvailableError(
                    f"Vendor {vendor_id} has no assignment on booking {booking_id}."
                )

            old_status = booking.booking_status
            booking = await uow.bookings.bookings.update(
                booking, {"booking_status": BookingStatus.IN_PROGRESS}
            )

            await self._write_status_history(
                uow, booking.id, old_status, BookingStatus.IN_PROGRESS, vendor_id
            )
            await self._write_history_event(
                uow,
                booking_id=booking.id,
                event_type=BookingEventType.STATUS_CHANGED,
                actor_type=BookingActorType.VENDOR,
                actor_id=vendor_id,
                event_label="Service started",
                context_data={"new_status": BookingStatus.IN_PROGRESS.value},
            )

            await uow.commit()
            return BookingResponse.model_validate(booking)

    async def complete_booking(
        self,
        booking_id: UUID,
        vendor_id: UUID,
    ) -> BookingResponse:
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)
            validate_status_transition_allowed(booking, "completed")

            old_status = booking.booking_status
            now = datetime.now(tz=timezone.utc)
            booking = await uow.bookings.bookings.update(
                booking,
                {
                    "booking_status": BookingStatus.COMPLETED,
                    "completed_at": now,
                },
            )

            await self._write_status_history(
                uow, booking.id, old_status, BookingStatus.COMPLETED, vendor_id
            )
            await self._write_history_event(
                uow,
                booking_id=booking.id,
                event_type=BookingEventType.STATUS_CHANGED,
                actor_type=BookingActorType.VENDOR,
                actor_id=vendor_id,
                event_label="Service completed",
                context_data={"new_status": BookingStatus.COMPLETED.value},
            )

            await uow.vendors.vendors.increment_completion_count(vendor_id)

            await uow.commit()

        # Side effect: trigger vendor payment release (stub)
        await self._release_vendor_payment(booking_id)
        return BookingResponse.model_validate(booking)

    async def _release_vendor_payment(self, booking_id: UUID) -> None:
        """Stub: release vendor payment after booking completion."""
        pass  # TODO: integrate with payment service

    # ── Vendor assignment ─────────────────────────────────────────────────────

    async def assign_vendor(
        self,
        booking_id: UUID,
        item_id: UUID,
        vendor_id: UUID,
        admin_id: UUID,
    ) -> BookingAssignmentInternal:
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)

            item = await uow.bookings.items.get_by_id(item_id)
            if item is None or item.booking_id != booking_id:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("BookingItem", str(item_id))

            # Validate vendor availability
            if booking.scheduled_start_time and booking.scheduled_end_time:
                await validate_vendor_availability_for_booking(
                    vendor_id=vendor_id,
                    event_date=booking.scheduled_date,
                    start_time=booking.scheduled_start_time,
                    end_time=booking.scheduled_end_time,
                    uow=uow,
                    exclude_booking_id=booking_id,
                )

            assignment = await uow.bookings.assignments.create(
                BookingAssignment(
                    booking_id=booking_id,
                    booking_item_id=item_id,
                    vendor_id=vendor_id,
                    assigned_by_id=admin_id,
                    assignment_status=AssignmentStatus.ASSIGNED,
                )
            )

            await self._write_history_event(
                uow,
                booking_id=booking_id,
                event_type=BookingEventType.VENDOR_ASSIGNED,
                actor_type=BookingActorType.ADMIN,
                actor_id=admin_id,
                event_label="Vendor assigned",
                is_customer_visible=False,
                context_data={
                    "vendor_id": str(vendor_id),
                    "item_id": str(item_id),
                    "assignment_id": str(assignment.id),
                },
            )

            await uow.commit()
            return BookingAssignmentInternal.model_validate(assignment)

    async def unassign_vendor(
        self,
        booking_id: UUID,
        assignment_id: UUID,
        admin_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            assignment = await uow.bookings.assignments.get_by_id(assignment_id)
            if assignment is None or assignment.booking_id != booking_id:
                raise AssignmentNotFoundError(str(assignment_id))

            await uow.bookings.assignments.delete(assignment)

            await self._write_history_event(
                uow,
                booking_id=booking_id,
                event_type=BookingEventType.VENDOR_UNASSIGNED,
                actor_type=BookingActorType.ADMIN,
                actor_id=admin_id,
                event_label="Vendor unassigned",
                is_customer_visible=False,
                context_data={"assignment_id": str(assignment_id)},
            )

            await uow.commit()

    # ── Cancellation ──────────────────────────────────────────────────────────

    async def request_cancellation(
        self,
        booking_id: UUID,
        customer_id: UUID,
        data: BookingCancellationCreate,
    ) -> BookingCancellationResponse:
        async with self._uow() as uow:
            booking = await validate_booking_ownership(booking_id, customer_id, uow)
            validate_cancellation_window(booking)
            # Validate that the booking can be cancelled from its current status
            validate_status_transition_allowed(booking, "cancelled")

            waive_fee = False
            membership = await uow.memberships.memberships.get_active_for_user(customer_id)
            if membership is not None:
                plan = await uow.memberships.plans.get_by_id(membership.plan_id)
                waive_fee = bool(plan and plan.cancellation_protection)

            fee = (
                Decimal("0.00")
                if waive_fee
                else calculate_cancellation_fee(booking.total_amount, CANCELLATION_FEE_PERCENTAGE)
            )
            refund = calculate_refund_amount(booking.total_amount, fee)

            now = datetime.now(tz=timezone.utc)
            cancellation = await uow.bookings.cancellations.create(
                BookingCancellation(
                    booking_id=booking_id,
                    cancelled_by_id=customer_id,
                    cancellation_reason=data.reason,
                    cancellation_notes=data.reason_detail,
                    cancelled_at=now,
                    refund_eligible=True,
                    refund_amount=refund,
                )
            )

            # Leave booking status as-is; cancellation record signals pending review.
            # Status transitions to CANCELLED are finalised by process_cancellation.
            old_status = booking.booking_status

            await self._write_status_history(
                uow,
                booking_id,
                old_status,
                old_status,  # no status change yet — request is pending admin review
                customer_id,
                reason=f"Cancellation requested: {data.reason}",
            )
            await self._write_history_event(
                uow,
                booking_id=booking_id,
                event_type=BookingEventType.CANCELLATION_REQUESTED,
                actor_type=BookingActorType.CUSTOMER,
                actor_id=customer_id,
                event_label="Cancellation requested",
                context_data={
                    "reason": str(data.reason),
                    "cancellation_fee": str(fee),
                    "refund_amount": str(refund),
                    "fee_waived_by_membership": waive_fee,
                },
            )

            await uow.commit()
            return BookingCancellationResponse.model_validate(cancellation)

    async def process_cancellation(
        self,
        booking_id: UUID,
        admin_id: UUID,
        approved: bool,
    ) -> BookingResponse:
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)

            new_status = BookingStatus.CANCELLED if approved else BookingStatus.CONFIRMED
            validate_status_transition_allowed(booking, new_status.value)
            old_status = booking.booking_status

            booking = await uow.bookings.bookings.update(
                booking, {"booking_status": new_status}
            )

            await self._write_status_history(
                uow, booking_id, old_status, new_status, admin_id
            )
            await self._write_history_event(
                uow,
                booking_id=booking_id,
                event_type=BookingEventType.ADMIN_OVERRIDE,
                actor_type=BookingActorType.ADMIN,
                actor_id=admin_id,
                event_label="Cancellation approved" if approved else "Cancellation rejected",
                is_customer_visible=True,
                context_data={"approved": approved, "new_status": new_status.value},
            )

            await uow.commit()

        if approved:
            # Side effect: process refund (stub)
            await self._process_refund(booking_id)

        return BookingResponse.model_validate(booking)

    async def _process_refund(self, booking_id: UUID) -> None:
        """Stub: initiate refund after cancellation approval."""
        pass  # TODO: integrate with payment service

    # ── Reschedule ────────────────────────────────────────────────────────────

    async def request_reschedule(
        self,
        booking_id: UUID,
        customer_id: UUID,
        data: BookingRescheduleCreate,
    ) -> BookingRescheduleResponse:
        async with self._uow() as uow:
            booking = await validate_booking_ownership(booking_id, customer_id, uow)
            validate_reschedule_window(booking)

            # Validate new vendor availability if vendor assigned
            if data.new_start_time and booking.scheduled_end_time:
                assignments = await uow.bookings.assignments.find_many(
                    uow.bookings.assignments._model.booking_id == booking_id,
                )
                for asgn in assignments:
                    await validate_vendor_availability_for_booking(
                        vendor_id=asgn.vendor_id,
                        event_date=data.new_date,
                        start_time=data.new_start_time,
                        end_time=booking.scheduled_end_time,
                        uow=uow,
                        exclude_booking_id=booking_id,
                    )

            reschedule = await uow.bookings.reschedules.create(
                BookingReschedule(
                    booking_id=booking_id,
                    requested_by_id=customer_id,
                    old_date=booking.scheduled_date,
                    new_date=data.new_date,
                    old_start_time=booking.scheduled_start_time,
                    new_start_time=data.new_start_time,
                    reason=data.reason,
                    status=RescheduleStatus.PENDING_APPROVAL,
                )
            )

            await self._write_history_event(
                uow,
                booking_id=booking_id,
                event_type=BookingEventType.RESCHEDULE_REQUESTED,
                actor_type=BookingActorType.CUSTOMER,
                actor_id=customer_id,
                event_label="Reschedule requested",
                context_data={
                    "old_date": str(booking.scheduled_date),
                    "new_date": str(data.new_date),
                    "reschedule_id": str(reschedule.id),
                },
            )

            await uow.commit()
            return BookingRescheduleResponse.model_validate(reschedule)

    async def process_reschedule(
        self,
        booking_id: UUID,
        reschedule_id: UUID,
        admin_id: UUID,
        approved: bool,
    ) -> BookingResponse:
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)
            reschedule = await uow.bookings.reschedules.get_by_id(reschedule_id)
            if reschedule is None or reschedule.booking_id != booking_id:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("BookingReschedule", str(reschedule_id))

            now = datetime.now(tz=timezone.utc)
            new_reschedule_status = (
                RescheduleStatus.APPROVED if approved else RescheduleStatus.REJECTED
            )
            await uow.bookings.reschedules.update(
                reschedule,
                {
                    "status": new_reschedule_status,
                    "approved_by_id": admin_id,
                    "approved_at": now,
                },
            )

            if approved:
                booking = await uow.bookings.bookings.update(
                    booking,
                    {
                        "scheduled_date": reschedule.new_date,
                        "scheduled_start_time": reschedule.new_start_time,
                    },
                )

            await self._write_history_event(
                uow,
                booking_id=booking_id,
                event_type=BookingEventType.RESCHEDULE_APPROVED if approved else BookingEventType.ADMIN_OVERRIDE,
                actor_type=BookingActorType.ADMIN,
                actor_id=admin_id,
                event_label="Reschedule approved" if approved else "Reschedule rejected",
                context_data={
                    "approved": approved,
                    "reschedule_id": str(reschedule_id),
                    "new_date": str(reschedule.new_date) if approved else None,
                },
            )

            await uow.commit()
            return BookingResponse.model_validate(booking)

    # ── Booking history (read-only) ───────────────────────────────────────────

    async def get_booking_history(
        self,
        booking_id: UUID,
        requester_id: UUID,
        requester_role: str,
    ) -> list[dict]:
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)

            if requester_role == "customer" and booking.customer_id != requester_id:
                raise BookingOwnershipError(
                    f"Booking {booking_id} does not belong to customer {requester_id}."
                )

            include_internal = requester_role in {"admin", "support"}
            history = await uow.bookings.history.find_by_booking(
                booking_id, include_internal=include_internal
            )
            return [
                {
                    "id": str(h.id),
                    "booking_id": str(h.booking_id),
                    "event_type": str(h.event_type),
                    "event_label": h.event_label,
                    "actor_type": str(h.actor_type),
                    "actor_id": str(h.actor_id) if h.actor_id else None,
                    "is_customer_visible": h.is_customer_visible,
                    "occurred_at": h.occurred_at.isoformat(),
                    "context_data": h.context_data,
                }
                for h in history
            ]

    async def get_booking_status_history(
        self,
        booking_id: UUID,
    ) -> list[BookingStatusHistoryResponse]:
        async with self._uow() as uow:
            await validate_booking_exists(booking_id, uow)
            records = await uow.bookings.status_history.find_by_booking(booking_id)
            return [BookingStatusHistoryResponse.model_validate(r) for r in records]

    # ── Invoice ───────────────────────────────────────────────────────────────

    async def get_booking_invoice(
        self,
        booking_id: UUID,
        customer_id: UUID,
    ) -> BookingInvoiceResponse:
        async with self._uow() as uow:
            booking = await validate_booking_ownership(booking_id, customer_id, uow)
            invoice = await uow.bookings.invoices.find_by_booking(booking_id)
            if invoice is None:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("BookingInvoice", f"booking_id={booking_id}")
            return BookingInvoiceResponse.model_validate(invoice)

    async def generate_booking_invoice(
        self,
        booking_id: UUID,
        admin_id: UUID,
    ) -> BookingInvoiceResponse:
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)

            # Return existing current invoice if present
            existing = await uow.bookings.invoices.find_by_booking(booking_id)
            if existing is not None and existing.is_current:
                return BookingInvoiceResponse.model_validate(existing)

            now = datetime.now(tz=timezone.utc)
            invoice_number = f"INV-{now.strftime('%Y%m%d')}-{str(booking_id)[:8].upper()}"

            invoice = await uow.bookings.invoices.create(
                BookingInvoice(
                    booking_id=booking_id,
                    invoice_number=invoice_number,
                    invoice_status=InvoiceStatus.DRAFT,
                    is_current=True,
                    invoice_date=now.date(),
                    billing_name="",  # Populated by billing service from customer profile
                    billing_address="",
                    subtotal=booking.subtotal,
                    discount_amount=booking.discount_amount,
                    taxable_amount=booking.subtotal - booking.discount_amount,
                    tax_amount=booking.tax_amount,
                    platform_fee=booking.platform_fee,
                    total_amount=booking.total_amount,
                    generated_at=now,
                )
            )

            await uow.commit()
            return BookingInvoiceResponse.model_validate(invoice)
