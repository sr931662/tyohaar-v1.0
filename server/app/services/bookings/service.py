from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
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
    BookingCustomerSummary,
    BookingDetailResponse,
    BookingFilters,
    BookingInvoiceResponse,
    BookingItemResponse,
    BookingResponse,
    BookingRescheduleCreate,
    BookingRescheduleResponse,
    BookingStatusHistoryResponse,
    BookingVendorSummary,
)
from app.services.base import BaseService
from app.services.exceptions import BusinessRuleError
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
    VendorAssignmentOwnershipError,
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

logger = logging.getLogger(__name__)


class BookingService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _scheduled_event_dt(self, data: BookingCreate) -> datetime:
        t = data.scheduled_start_time or time(0, 0, 0)
        d = data.scheduled_date
        return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=timezone.utc)

    async def _resolve_vendor_actor_user_id(self, uow, vendor_id: UUID) -> UUID:
        """
        Booking history/status tables attribute actors via users.id, while
        vendor-facing endpoints authenticate with vendors.id.
        """
        vendor = await uow.vendors.vendors.get_by_id(vendor_id)
        if vendor is None:
            raise VendorNotAvailableError(f"Vendor {vendor_id} does not exist.")
        return vendor.user_id

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
            # Idempotency safety net: if the customer already has a PENDING
            # booking for this exact package + date created in the last few
            # minutes, return it instead of creating a duplicate celebration
            # + booking. Covers a client back-navigation/resubmit race
            # rather than a client-supplied idempotency key.
            recent_cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
            duplicate_candidates = await uow.bookings.bookings.find_many(
                uow.bookings.bookings._model.customer_id == customer_id,
                uow.bookings.bookings._model.package_id == data.package_id,
                uow.bookings.bookings._model.scheduled_date == data.scheduled_date,
                uow.bookings.bookings._model.booking_status == BookingStatus.PENDING,
                uow.bookings.bookings._model.created_at >= recent_cutoff,
            )
            if duplicate_candidates:
                existing = max(duplicate_candidates, key=lambda b: b.created_at)
                info = await self._attach_package_info(uow, [existing])
                response = BookingResponse.model_validate(existing)
                response.package_name, response.package_cover_url = info.get(
                    existing.package_id, (None, None)
                )
                return response

            # Validate package exists and is available
            package = await validate_package_available(data.package_id, data.scheduled_date, uow)

            celebration_id = data.celebration_id
            occasion_id = data.occasion_id
            if celebration_id is None:
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
            package_items = await uow.packages.items.find_by_package_including_common(data.package_id)
            selected_items = [i for i in package_items if i.is_mandatory]

            # 2. Fetch selected optional items (add-ons)
            if data.item_ids:
                optional_items = [i for i in package_items if not i.is_mandatory and i.id in data.item_ids]
                selected_items.extend(optional_items)

            # 3. Resolve per-item quantities — customer may request more than
            # the package template's default (e.g. 5 balloons isn't enough
            # for a bigger event), clamped to [template quantity, max_quantity].
            item_quantities = data.item_quantities or {}

            def _resolve_qty(pi) -> int:
                requested = item_quantities.get(str(pi.id))
                if requested is None:
                    return pi.quantity
                qty = max(int(requested), pi.quantity)
                if pi.max_quantity is not None:
                    qty = min(qty, pi.max_quantity)
                return qty

            # 4. Calculate financials — package base price + selected items.
            # Package.base_price is the package's own starting price; item
            # rows are line-item add-ons/inclusions on top of it, not a
            # replacement for it (previously this only summed items, so a
            # package with no items priced the booking at ₹0 subtotal).
            items_total = sum((i.base_price * _resolve_qty(i)) for i in selected_items)
            subtotal = (package.base_price or Decimal("0.00")) + items_total
            platform_fee = Decimal("0.00")  # Platform fee removed project-wide.

            # 4b. Discount engine — evaluates automatic discounts plus the
            # optional coupon_code, in the SAME transaction as this booking
            # so eligibility reads are consistent with what's being written.
            from app.services.payments.discount_engine import DiscountEngine
            discount_result = await DiscountEngine().evaluate(
                uow,
                customer_id=customer_id,
                subtotal=subtotal,
                package_id=data.package_id,
                occasion_id=occasion_id,
                coupon_code=data.coupon_code,
            )
            discount_amount = discount_result.total_discount
            applied_coupon_ids = [str(item.coupon_id) for item in discount_result.applied_discounts]

            # Tax is computed on the post-discount taxable base, matching what
            # invoice generation already assumes (taxable_amount = subtotal -
            # discount_amount) — see verify_payment's invoice block.
            taxable_amount = subtotal - discount_amount
            tax_rate = Decimal("0.18")
            tax_amount = (taxable_amount * tax_rate).quantize(Decimal("0.01"))
            total_amount = taxable_amount + tax_amount + platform_fee

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
                discount_amount=discount_amount,
                applied_coupon_ids=applied_coupon_ids or None,
                tax_amount=tax_amount,
                platform_fee=platform_fee,
                total_amount=total_amount,
                amount_paid=Decimal("0.00"),
                amount_due=total_amount,
                special_instructions=data.special_instructions,
                customization_note=data.customization_note,
                balloon_color_mode=data.balloon_color_mode,
                balloon_colors=data.balloon_colors,
            )
            booking = await uow.bookings.bookings.create(booking)

            # 5. Create BookingItem records
            for idx, pi in enumerate(selected_items):
                qty = _resolve_qty(pi)
                item = BookingItem(
                    booking_id=booking.id,
                    package_item_id=pi.id,
                    name=pi.name,
                    description=pi.description,
                    quantity=qty,
                    unit=pi.unit,
                    unit_price=pi.base_price,
                    final_price=pi.base_price * qty,
                    is_mandatory=pi.is_mandatory,
                    is_addon=not pi.is_mandatory,
                    display_order=idx,
                    prep_time_minutes=pi.prep_time_minutes,
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

    async def _attach_package_info(
        self, uow, bookings: list[Booking]
    ) -> dict[UUID, tuple[str | None, str | None]]:
        """Batch-fetch package name/cover image for a list of bookings, keyed by package_id."""
        package_ids = list({b.package_id for b in bookings if b.package_id})
        packages = await uow.packages.packages.get_by_ids(package_ids)
        return {p.id: (p.name, p.cover_image_url) for p in packages}

    async def _attach_celebration_info(
        self, uow, bookings: list[Booking]
    ) -> dict[UUID, tuple[str | None, UUID | None, str | None]]:
        """
        Batch-fetch the celebration title and selected customization theme
        (id + name) for a list of bookings, keyed by celebration_id. Both
        live on Celebration, not Booking, since a booking can be one of
        several against the same celebration (reschedules, multi-vendor
        line items) — the celebration is the durable "event", the booking
        is one service engagement within it.
        """
        from sqlalchemy import select
        from app.models.occasions.celebration import Celebration
        from app.models.occasions.occasion_theme import OccasionTheme

        celebration_ids = list({b.celebration_id for b in bookings if b.celebration_id})
        if not celebration_ids:
            return {}
        rows = await uow.session.execute(
            select(Celebration.id, Celebration.title, Celebration.theme_id, OccasionTheme.name)
            .outerjoin(OccasionTheme, OccasionTheme.id == Celebration.theme_id)
            .where(Celebration.id.in_(celebration_ids))
        )
        return {
            cid: (title, theme_id, theme_name)
            for cid, title, theme_id, theme_name in rows.all()
        }

    async def _attach_customer_info(self, uow, customer_id: UUID) -> BookingCustomerSummary | None:
        """Fetch a lightweight customer contact snapshot for admin/support-only display."""
        user = await uow.users.users.get_by_id(customer_id)
        if user is None:
            return None
        return BookingCustomerSummary(
            id=user.id,
            full_name=user.full_name,
            phone=user.phone,
            email=user.email,
        )

    async def _attach_vendor_info(self, uow, package_id: UUID | None) -> BookingVendorSummary | None:
        """
        Fetch the package-owner vendor's summary (business name + contact) for
        admin/support-only display. This is the vendor whose package was
        selected — not necessarily the only vendor delivering line items
        (see BookingAssignment for per-item dispatch).
        """
        if package_id is None:
            return None
        package = await uow.packages.packages.get_by_id(package_id)
        if package is None:
            return None
        vendor = await uow.vendors.vendors.get_by_id(package.vendor_id)
        if vendor is None:
            return None
        vendor_user = await uow.users.users.get_by_id(vendor.user_id)
        return BookingVendorSummary(
            id=vendor.id,
            business_name=vendor.business_name,
            phone=vendor_user.phone if vendor_user else None,
            email=vendor_user.email if vendor_user else None,
            verification_status=vendor.verification_status,
        )

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

            info = await self._attach_package_info(uow, [booking])
            name, cover_url = info.get(booking.package_id, (None, None))
            celeb_info = await self._attach_celebration_info(uow, [booking])
            title, theme_id, theme_name = celeb_info.get(booking.celebration_id, (None, None, None))
            response = BookingDetailResponse.model_validate(booking)
            response.package_name = name
            response.package_cover_url = cover_url
            response.celebration_title = title
            response.theme_id = theme_id
            response.theme_name = theme_name

            # Customer contact + vendor identity are only ever attached for
            # admin/support requesters — never for the customer's own view or
            # a vendor's own view of the same endpoint, to preserve the
            # existing invariant that customers and vendors never see each
            # other's identity through this shared endpoint.
            if requester_role in ("admin", "super_admin"):
                response.customer = await self._attach_customer_info(uow, booking.customer_id)
                response.vendor = await self._attach_vendor_info(uow, booking.package_id)

            return response

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
            if filters.celebration_id is not None:
                conditions.append(uow.bookings.bookings._model.celebration_id == filters.celebration_id)
            page = await uow.bookings.bookings.cursor_paginate(
                *conditions,
                cursor=cursor,
                limit=limit,
            )
            info = await self._attach_package_info(uow, page.items)
            celeb_info = await self._attach_celebration_info(uow, page.items)
            items = []
            for b in page.items:
                item = BookingResponse.model_validate(b)
                item.package_name, item.package_cover_url = info.get(b.package_id, (None, None))
                item.celebration_title, item.theme_id, item.theme_name = celeb_info.get(
                    b.celebration_id, (None, None, None)
                )
                items.append(item)
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
            from sqlalchemy import or_, and_
            from app.models.packages.package import Package
            from app.models.bookings.booking import Booking

            # 1. Ownership logic: assigned or owned package
            assignments = await uow.bookings.assignments.find_by_vendor(vendor_id, limit=1000)
            assigned_booking_ids = {a.booking_id for a in assignments}

            owned_packages = await uow.packages.packages.find_many(Package.vendor_id == vendor_id)
            owned_package_ids = [p.id for p in owned_packages]

            if not assigned_booking_ids and not owned_package_ids:
                return CursorPage(items=[], next_cursor=None, has_more=False)

            # 2. Build Query Conditions
            # Start with identity: must be in assigned list OR match an owned package
            identity_clause = []
            if assigned_booking_ids:
                identity_clause.append(Booking.id.in_(list(assigned_booking_ids)))
            if owned_package_ids:
                identity_clause.append(Booking.package_id.in_(owned_package_ids))

            # Combine identity with OR
            base_condition = or_(*identity_clause)

            # Functional Filters
            status_filter = None
            if filters.booking_status:
                logger.info(f"Filtering vendor bookings by status: {filters.booking_status}")
                # Use the value explicitly to be safe with string enums
                status_val = str(filters.booking_status.value) if hasattr(filters.booking_status, 'value') else str(filters.booking_status)
                status_filter = (Booking.booking_status == status_val)

            search_filter = None
            if filters.search and filters.search.strip():
                logger.info(f"Filtering vendor bookings by search: {filters.search}")
                search_filter = Booking.booking_number.ilike(f"{filters.search.strip().lower()}%")

            # Final list of filters to AND
            final_filters = [base_condition]
            if status_filter is not None:
                final_filters.append(status_filter)
            if search_filter is not None:
                final_filters.append(search_filter)

            # 3. Fetch
            page = await uow.bookings.bookings.cursor_paginate(
                and_(*final_filters),
                cursor=cursor,
                limit=limit,
            )

            # 4. Hydrate
            info = await self._attach_package_info(uow, page.items)
            celeb_info = await self._attach_celebration_info(uow, page.items)
            items = []
            for b in page.items:
                item = BookingResponse.model_validate(b)
                item.package_name, item.package_cover_url = info.get(b.package_id, (None, None))
                item.celebration_title, item.theme_id, item.theme_name = celeb_info.get(
                    b.celebration_id, (None, None, None)
                )
                items.append(item)

            return CursorPage(items=items, next_cursor=page.next_cursor, has_more=page.has_next)

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

        await self.notify_vendor_if_confirmed_and_paid(booking_id)
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

            actor_user_id = await self._resolve_vendor_actor_user_id(uow, vendor_id)
            old_status = booking.booking_status
            booking = await uow.bookings.bookings.update(
                booking, {"booking_status": BookingStatus.IN_PROGRESS}
            )

            await self._write_status_history(
                uow, booking.id, old_status, BookingStatus.IN_PROGRESS, actor_user_id
            )
            await self._write_history_event(
                uow,
                booking_id=booking.id,
                event_type=BookingEventType.STATUS_CHANGED,
                actor_type=BookingActorType.VENDOR,
                actor_id=actor_user_id,
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

            actor_user_id = await self._resolve_vendor_actor_user_id(uow, vendor_id)
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
                uow, booking.id, old_status, BookingStatus.COMPLETED, actor_user_id
            )
            await self._write_history_event(
                uow,
                booking_id=booking.id,
                event_type=BookingEventType.STATUS_CHANGED,
                actor_type=BookingActorType.VENDOR,
                actor_id=actor_user_id,
                event_label="Service completed",
                context_data={"new_status": BookingStatus.COMPLETED.value},
            )

            await uow.vendors.vendors.increment_completion_count(vendor_id)

            await uow.commit()

        # Side effect: trigger vendor payment release (stub)
        await self._release_vendor_payment(booking_id)
        return BookingResponse.model_validate(booking)

    async def update_pst(
        self,
        booking_id: UUID,
        vendor_id: UUID,
        pst_at: datetime,
    ) -> BookingResponse:
        """
        Allows a vendor to set the Preparation Starting Time [PST] — the full
        date + time they will arrive and begin preparation — for a booking they
        are assigned to (or whose package they own). Notifies the customer on
        all channels (in-app, email, push) once saved.
        """
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)

            # Security: Ensure this vendor has an ACCEPTED assignment for this booking
            # We use the internal assignment mapping to verify.
            assignments = await uow.bookings.assignments.find_many(
                uow.bookings.assignments._model.booking_id == booking_id,
                uow.bookings.assignments._model.vendor_id == vendor_id,
                uow.bookings.assignments._model.assignment_status == AssignmentStatus.ACCEPTED,
            )

            if not assignments:
                # If no assignment found, check if the package belongs to this vendor
                package = await uow.packages.packages.get_by_id(booking.package_id)
                if package is None or package.vendor_id != vendor_id:
                    raise VendorNotAvailableError(
                        f"Vendor {vendor_id} is not authorized to update PST for booking {booking_id}."
                    )

            actor_user_id = await self._resolve_vendor_actor_user_id(uow, vendor_id)
            booking = await uow.bookings.bookings.update(
                booking,
                {
                    "preparation_start_at": pst_at,
                    # Mirror the time component into the legacy column so older
                    # readers of preparation_start_time keep working.
                    "preparation_start_time": pst_at.time(),
                },
            )

            pretty = pst_at.strftime("%d %b %Y, %I:%M %p")
            await self._write_history_event(
                uow,
                booking_id=booking.id,
                event_type=BookingEventType.SCHEDULE_CHANGED,
                actor_type=BookingActorType.VENDOR,
                actor_id=actor_user_id,
                event_label="Preparation time set",
                description=f"Vendor set preparation start to {pretty}",
                context_data={"preparation_start_at": pst_at.isoformat()},
            )

            customer_id = booking.customer_id
            booking_number = booking.booking_number
            await uow.commit()

        await self._notify_customer_pst(customer_id, booking_id, booking_number, pst_at)
        return BookingResponse.model_validate(booking)

    async def _notify_customer_pst(
        self,
        customer_id: UUID,
        booking_id: UUID,
        booking_number: str,
        pst_at: datetime,
    ) -> None:
        """
        Tell the customer their vendor has scheduled a preparation start time,
        fanning out across every channel: IN_APP (notification screen), EMAIL,
        and PUSH (device status bar). Email/push are best-effort and no-op
        silently until SMTP / Firebase credentials are configured.
        """
        from app.models.enums import NotificationChannel, NotificationType
        from app.schemas.notifications.create import NotificationCreate
        from app.services.notifications.service import NotificationService

        pretty = pst_at.strftime("%d %b %Y at %I:%M %p")
        title = "Preparation time scheduled"
        body = (
            f"Your vendor for booking {booking_number} will begin preparation "
            f"on {pretty}."
        )
        action_url = f"/bookings/{booking_id}"
        service = NotificationService()
        for channel in (
            NotificationChannel.IN_APP,
            NotificationChannel.EMAIL,
            NotificationChannel.PUSH,
        ):
            try:
                await service.send_notification(
                    user_id=customer_id,
                    data=NotificationCreate(
                        user_id=customer_id,
                        notification_type=NotificationType.BOOKING_UPDATED,
                        channel=channel,
                        title=title,
                        body=body,
                        action_url=action_url,
                        reference_type="booking",
                        reference_id=booking_id,
                    ),
                )
            except Exception:
                # One channel failing (e.g. transient FCM/SMTP error) must not
                # block the others or fail the PST update itself.
                logger.exception(
                    "PST notification failed on channel %s for booking %s",
                    channel, booking_id,
                )

    async def notify_vendor_if_confirmed_and_paid(self, booking_id: UUID) -> None:
        """
        Notify the vendor whose package was selected once a booking is BOTH
        confirmed (booking_status == CONFIRMED) and paid (payment_status ==
        COMPLETED). Safe to call from either the confirmation path or the
        payment-completion path, in any order — idempotent via a lookup on
        existing BOOKING_CONFIRMED notifications for this booking+vendor.
        """
        from app.models.enums import NotificationChannel, NotificationType
        from app.schemas.notifications.create import NotificationCreate
        from app.services.notifications.service import NotificationService

        async with self._uow() as uow:
            booking = await uow.bookings.bookings.get_by_id(booking_id)
            if booking is None:
                return
            if booking.booking_status != BookingStatus.CONFIRMED or booking.payment_status != PaymentStatus.COMPLETED:
                return

            package = await uow.packages.packages.get_by_id(booking.package_id)
            if package is None:
                return
            vendor = await uow.vendors.vendors.get_by_id(package.vendor_id)
            if vendor is None:
                return

            existing = await uow.notifications.notifications.find_many(
                uow.notifications.notifications._model.recipient_id == vendor.user_id,
                uow.notifications.notifications._model.reference_type == "booking",
                uow.notifications.notifications._model.reference_id == booking.id,
                uow.notifications.notifications._model.notification_type == NotificationType.BOOKING_CONFIRMED,
            )
            if existing:
                return

            vendor_user_id = vendor.user_id

        await NotificationService().send_notification(
            user_id=vendor_user_id,
            data=NotificationCreate(
                user_id=vendor_user_id,
                notification_type=NotificationType.BOOKING_CONFIRMED,
                channel=NotificationChannel.IN_APP,
                title="New confirmed booking",
                body=f"Booking {booking.booking_number} is confirmed and paid. "
                     f"Please provide your Preparation Starting Time (PST).",
                reference_type="booking",
                reference_id=booking.id,
            ),
        )

    async def _release_vendor_payment(self, booking_id: UUID) -> None:
        """
        Queue a PENDING VendorSettlement for each vendor who delivered an item
        on this booking, after service completion.

        Gross amount per vendor is the sum of `final_price` for the booking
        items they were ACCEPTED/COMPLETED-assigned to. `platform_fee` mirrors
        the same PLATFORM_FEE_PERCENTAGE applied when the booking was priced;
        commission/TDS/GST are left at 0 pending finance's rate configuration
        and are finalised by admin before payout, matching the existing
        settlement-review workflow (see VendorSettlement.status).
        """
        from app.models.enums import SettlementStatus
        from app.models.vendors.vendor_settlement import VendorSettlement
        from app.services.payments.constants import PLATFORM_FEE_PERCENTAGE

        async with self._uow() as uow:
            items = await uow.bookings.items.find_many(
                uow.bookings.items._model.booking_id == booking_id,
            )
            if not items:
                return

            assignments = await uow.bookings.assignments.find_many(
                uow.bookings.assignments._model.booking_id == booking_id,
            )
            vendor_by_item = {
                a.booking_item_id: a.vendor_id
                for a in assignments
                if a.assignment_status in (AssignmentStatus.ACCEPTED, AssignmentStatus.COMPLETED)
            }

            gross_by_vendor: dict[UUID, Decimal] = {}
            for item in items:
                vendor_id = vendor_by_item.get(item.id)
                if vendor_id is None:
                    continue
                gross_by_vendor[vendor_id] = gross_by_vendor.get(vendor_id, Decimal("0")) + item.final_price

            if not gross_by_vendor:
                return

            booking = await uow.bookings.bookings.get_by_id(booking_id)
            period = booking.scheduled_date if booking else datetime.now(tz=timezone.utc).date()

            for vendor_id, gross in gross_by_vendor.items():
                fee = (gross * PLATFORM_FEE_PERCENTAGE).quantize(Decimal("0.01"))
                await uow.vendors.settlements.create_from_dict({
                    "vendor_id": vendor_id,
                    "booking_id": booking_id,
                    "gross_amount": gross,
                    "commission_amount": Decimal("0.00"),
                    "platform_fee": fee,
                    "tds_amount": Decimal("0.00"),
                    "gst_on_fee": Decimal("0.00"),
                    "net_amount": gross - fee,
                    "settlement_period_start": period,
                    "settlement_period_end": period,
                    "status": SettlementStatus.PENDING,
                })

            await uow.commit()

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

    async def update_booking_item_prep_time(
        self,
        booking_id: UUID,
        item_id: UUID,
        vendor_id: UUID,
        prep_time_minutes: int,
    ) -> BookingItemResponse:
        """Vendor sets/updates the setup/prep time required before this item's start."""
        async with self._uow() as uow:
            item = await uow.bookings.items.get_by_id(item_id)
            if item is None or item.booking_id != booking_id:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("BookingItem", str(item_id))

            assignment = await uow.bookings.assignments.find_one(
                uow.bookings.assignments._model.booking_item_id == item_id,
                uow.bookings.assignments._model.vendor_id == vendor_id,
            )
            if assignment is None:
                raise VendorAssignmentOwnershipError(
                    f"Vendor {vendor_id} is not assigned to booking item {item_id}."
                )

            updated = await uow.bookings.items.update(
                item, {"prep_time_minutes": prep_time_minutes}
            )
            await uow.commit()
            return BookingItemResponse.model_validate(updated)

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
            # Side effect: process refund
            await self._process_refund(booking_id, admin_id)

        return BookingResponse.model_validate(booking)

    async def _process_refund(self, booking_id: UUID, admin_id: UUID) -> None:
        """
        Look up the booking's completed payment and the approved cancellation's
        refund_amount, then delegate to PaymentService.initiate_refund (which
        already handles the ledger entry and gateway refund call).
        """
        from app.schemas.payments import RefundCreate
        from app.services.payments.service import PaymentService

        async with self._uow() as uow:
            cancellation = await uow.bookings.cancellations.find_by_booking(booking_id)
            if cancellation is None or not cancellation.refund_eligible or not cancellation.refund_amount:
                return
            refund_amount = cancellation.refund_amount

            payments = await uow.payments.payments.find_by_booking(booking_id)
            completed_payment = next(
                (p for p in payments if p.payment_status == PaymentStatus.COMPLETED), None
            )
            if completed_payment is None or refund_amount <= 0:
                return
            payment_id = completed_payment.id

        payment_service = PaymentService()
        await payment_service.initiate_refund(
            payment_id=payment_id,
            data=RefundCreate(
                payment_id=payment_id,
                booking_id=booking_id,
                amount=refund_amount,
                reason="Booking cancellation approved",
            ),
            admin_id=admin_id,
        )

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

    # ── Multimedia (vendor-uploaded event media) ────────────────────────────

    async def _vendor_owns_booking(self, uow, booking: Booking, vendor_id: UUID) -> bool:
        """
        A vendor is eligible for a booking through either of the two sources
        `list_vendor_bookings` already recognizes: an explicit BookingAssignment
        row (multi-vendor bookings), or direct ownership of the booking's
        package (the common single-vendor case, which never gets an
        assignment row at creation). Keeping these in sync matters — a vendor
        who sees a booking in "My Bookings" must see it in Multimedia too.
        """
        from app.models.packages.package import Package

        assignments = await uow.bookings.assignments.find_many(
            uow.bookings.assignments._model.booking_id == booking.id,
            uow.bookings.assignments._model.vendor_id == vendor_id,
        )
        if assignments:
            return True

        package = await uow.packages.packages.get_by_id(booking.package_id)
        return package is not None and package.vendor_id == vendor_id

    # Once a booking is confirmed, the vendor's engagement is locked in —
    # media (e.g. pre-event decor shots, or the event itself once underway)
    # may be uploaded from that point on, not only after final completion.
    _MEDIA_UPLOAD_ELIGIBLE_STATUSES = {
        BookingStatus.CONFIRMED,
        BookingStatus.IN_PROGRESS,
        BookingStatus.COMPLETED,
    }

    async def assert_vendor_media_upload_allowed(
        self,
        booking_id: UUID,
        vendor_id: UUID,
    ) -> Booking:
        """
        Gate for the vendor multimedia-upload endpoint: the calling vendor
        must be eligible for this booking (assigned or package owner), and
        the booking must be at least confirmed.
        """
        async with self._uow() as uow:
            booking = await validate_booking_exists(booking_id, uow)

            if not await self._vendor_owns_booking(uow, booking, vendor_id):
                raise VendorNotAvailableError(
                    f"Vendor {vendor_id} is not assigned to booking {booking_id}."
                )

            if booking.booking_status not in self._MEDIA_UPLOAD_ELIGIBLE_STATUSES:
                raise BusinessRuleError(
                    "Media can only be uploaded once the booking is confirmed."
                )

            return booking

    async def _media_counts_by_booking(
        self, session, booking_ids: list[UUID]
    ) -> dict[UUID, tuple[int, int, str | None]]:
        """Returns {booking_id: (image_count, video_count, first_thumbnail_url)}."""
        from sqlalchemy import func, select as sa_select
        from app.models.media.image import Image
        from app.models.media.video import Video

        counts: dict[UUID, tuple[int, int, str | None]] = {bid: (0, 0, None) for bid in booking_ids}
        if not booking_ids:
            return counts

        image_rows = (
            await session.execute(
                sa_select(Image.entity_id, func.count())
                .where(
                    Image.entity_type == "booking",
                    Image.entity_id.in_(booking_ids),
                    Image.deleted_at.is_(None),
                )
                .group_by(Image.entity_id)
            )
        ).all()
        thumb_rows = (
            await session.execute(
                sa_select(Image.entity_id, Image.thumbnail_url, Image.url)
                .where(
                    Image.entity_type == "booking",
                    Image.entity_id.in_(booking_ids),
                    Image.deleted_at.is_(None),
                )
                .order_by(Image.created_at.asc())
            )
        ).all()
        video_rows = (
            await session.execute(
                sa_select(Video.entity_id, func.count())
                .where(
                    Video.entity_type == "booking",
                    Video.entity_id.in_(booking_ids),
                    Video.deleted_at.is_(None),
                )
                .group_by(Video.entity_id)
            )
        ).all()

        thumbs: dict[UUID, str | None] = {}
        for entity_id, thumbnail_url, url in thumb_rows:
            thumbs.setdefault(entity_id, thumbnail_url or url)

        image_count_map = {entity_id: cnt for entity_id, cnt in image_rows}
        video_count_map = {entity_id: cnt for entity_id, cnt in video_rows}

        for bid in booking_ids:
            counts[bid] = (
                int(image_count_map.get(bid, 0)),
                int(video_count_map.get(bid, 0)),
                thumbs.get(bid),
            )
        return counts

    async def list_vendor_booking_media(self, vendor_id: UUID) -> list["BookingMediaSummary"]:
        """
        Bookings this vendor is eligible for (assigned, or the direct
        package owner — same two-source definition as list_vendor_bookings),
        with media counts, for the vendor portal's Multimedia section.
        Upload is only allowed once completed.
        """
        from sqlalchemy import or_, select as sa_select
        from app.models.packages.package import Package
        from app.models.users.user import User
        from app.schemas.bookings import BookingMediaSummary

        async with self._uow() as uow:
            session = uow.session
            assert session is not None

            assignments = await uow.bookings.assignments.find_by_vendor(vendor_id, limit=1000)
            booking_ids = {a.booking_id for a in assignments}

            owned_packages = await uow.packages.packages.find_many(
                Package.vendor_id == vendor_id
            )
            owned_package_ids = [p.id for p in owned_packages]

            conditions = []
            if booking_ids:
                conditions.append(Booking.id.in_(booking_ids))
            if owned_package_ids:
                conditions.append(Booking.package_id.in_(owned_package_ids))

            if not conditions:
                return []

            rows = (
                await session.execute(
                    sa_select(Booking, User, Package)
                    .join(User, User.id == Booking.customer_id)
                    .join(Package, Package.id == Booking.package_id)
                    .where(
                        or_(*conditions) if len(conditions) > 1 else conditions[0],
                        Booking.deleted_at.is_(None),
                    )
                    .order_by(Booking.scheduled_date.desc())
                )
            ).all()

            booking_ids = [b.id for b, _, _ in rows]
            media_counts = await self._media_counts_by_booking(session, booking_ids)

            return [
                BookingMediaSummary(
                    booking_id=booking.id,
                    booking_number=booking.booking_number,
                    event_title=package.name,
                    scheduled_date=booking.scheduled_date,
                    booking_status=booking.booking_status,
                    customer_name=getattr(user, "full_name", None),
                    customer_email=getattr(user, "email", None),
                    can_upload=booking.booking_status in self._MEDIA_UPLOAD_ELIGIBLE_STATUSES,
                    image_count=media_counts[booking.id][0],
                    video_count=media_counts[booking.id][1],
                    thumbnail_url=media_counts[booking.id][2],
                )
                for booking, user, package in rows
            ]

    async def list_admin_booking_media(
        self, *, skip: int = 0, limit: int = 20
    ) -> tuple[list["BookingMediaSummary"], int]:
        """
        Paginated list of bookings that have at least one vendor-uploaded
        image or video attached, for the admin Operations > Multimedia page.
        """
        from sqlalchemy import exists, func, select as sa_select, or_
        from app.models.media.image import Image
        from app.models.media.video import Video
        from app.models.packages.package import Package
        from app.models.users.user import User
        from app.schemas.bookings import BookingMediaSummary

        async with self._uow() as uow:
            session = uow.session
            assert session is not None

            has_image = exists(
                sa_select(Image.id).where(
                    Image.entity_type == "booking",
                    Image.entity_id == Booking.id,
                    Image.deleted_at.is_(None),
                )
            )
            has_video = exists(
                sa_select(Video.id).where(
                    Video.entity_type == "booking",
                    Video.entity_id == Booking.id,
                    Video.deleted_at.is_(None),
                )
            )
            base_conditions = [Booking.deleted_at.is_(None), or_(has_image, has_video)]

            total = (
                await session.execute(
                    sa_select(func.count()).select_from(Booking).where(*base_conditions)
                )
            ).scalar_one()

            rows = (
                await session.execute(
                    sa_select(Booking, User, Package)
                    .join(User, User.id == Booking.customer_id)
                    .join(Package, Package.id == Booking.package_id)
                    .where(*base_conditions)
                    .order_by(Booking.scheduled_date.desc())
                    .offset(skip)
                    .limit(limit)
                )
            ).all()

            booking_ids = [b.id for b, _, _ in rows]
            media_counts = await self._media_counts_by_booking(session, booking_ids)

            summaries = [
                BookingMediaSummary(
                    booking_id=booking.id,
                    booking_number=booking.booking_number,
                    event_title=package.name,
                    scheduled_date=booking.scheduled_date,
                    booking_status=booking.booking_status,
                    customer_name=getattr(user, "full_name", None),
                    customer_email=getattr(user, "email", None),
                    can_upload=False,
                    image_count=media_counts[booking.id][0],
                    video_count=media_counts[booking.id][1],
                    thumbnail_url=media_counts[booking.id][2],
                )
                for booking, user, package in rows
            ]
            return summaries, int(total)
