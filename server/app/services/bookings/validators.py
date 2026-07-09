from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from app.models.bookings.booking import Booking
from app.repositories.unit_of_work import UnitOfWork
from app.services.bookings.constants import (
    BOOKING_CUTOFF_HOURS,
    CANCELLATION_WINDOW_HOURS,
    RESCHEDULE_WINDOW_HOURS,
)
from app.services.bookings.exceptions import (
    BookingCancellationWindowError,
    BookingCutoffError,
    BookingNotFoundError,
    BookingOwnershipError,
    BookingRescheduleWindowError,
    BookingStatusTransitionError,
    VendorNotAvailableError,
)
from app.services.bookings.helpers import validate_status_transition
from app.services.packages.exceptions import PackageNotFoundError


async def validate_booking_exists(
    booking_id: UUID,
    uow: UnitOfWork,
) -> Booking:
    """Return the Booking or raise BookingNotFoundError."""
    booking = await uow.bookings.bookings.get_by_id(booking_id)
    if booking is None:
        raise BookingNotFoundError(str(booking_id))
    return booking


async def validate_booking_ownership(
    booking_id: UUID,
    customer_id: UUID,
    uow: UnitOfWork,
) -> Booking:
    """Return the Booking if it belongs to customer_id, else raise."""
    booking = await validate_booking_exists(booking_id, uow)
    if booking.customer_id != customer_id:
        raise BookingOwnershipError(
            f"Booking {booking_id} does not belong to customer {customer_id}."
        )
    return booking


def validate_status_transition_allowed(
    booking: Booking,
    new_status: str,
) -> None:
    """Raise BookingStatusTransitionError if the transition is invalid."""
    current = str(booking.booking_status.value) if hasattr(booking.booking_status, "value") else str(booking.booking_status)
    if not validate_status_transition(current, new_status):
        raise BookingStatusTransitionError(current, new_status)


def _scheduled_datetime(booking: Booking) -> datetime:
    """Combine booking.scheduled_date with scheduled_start_time (or midnight) as UTC."""
    d = booking.scheduled_date
    t = booking.scheduled_start_time or time(0, 0, 0)
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=timezone.utc)


def validate_cancellation_window(booking: Booking) -> None:
    """Raise BookingCancellationWindowError if outside the cancellation window."""
    from app.services.bookings.helpers import is_booking_cancellable
    event_dt = _scheduled_datetime(booking)
    if not is_booking_cancellable(event_dt, CANCELLATION_WINDOW_HOURS):
        raise BookingCancellationWindowError()


def validate_reschedule_window(booking: Booking) -> None:
    """Raise BookingRescheduleWindowError if outside the reschedule window."""
    from app.services.bookings.helpers import is_booking_reschedule_eligible
    event_dt = _scheduled_datetime(booking)
    if not is_booking_reschedule_eligible(event_dt, RESCHEDULE_WINDOW_HOURS):
        raise BookingRescheduleWindowError()


def validate_booking_cutoff(event_date: datetime) -> None:
    """
    Raise BookingCutoffError if event_date is less than BOOKING_CUTOFF_HOURS from now.
    event_date should be a timezone-aware datetime representing the scheduled event start.
    """
    from datetime import timedelta
    now = datetime.now(tz=timezone.utc)
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    if now > event_date - timedelta(hours=BOOKING_CUTOFF_HOURS):
        raise BookingCutoffError()


async def validate_vendor_availability_for_booking(
    vendor_id: UUID,
    event_date: date,
    start_time: time,
    end_time: time,
    uow: UnitOfWork,
    exclude_booking_id: UUID | None = None,
) -> None:
    """
    Raise VendorNotAvailableError if the vendor already has a confirmed/in-progress
    booking that overlaps the requested date and time window.
    """
    from app.models.bookings.booking import Booking as BookingModel
    from app.models.bookings.booking_assignment import BookingAssignment
    from app.models.enums import BookingStatus

    # Find assignments for this vendor on the same date
    assignments = await uow.bookings.assignments.find_by_vendor(vendor_id, limit=200)
    for assignment in assignments:
        # Skip if this is the booking we're updating
        if exclude_booking_id is not None and assignment.booking_id == exclude_booking_id:
            continue

        booking = await uow.bookings.bookings.get_by_id(assignment.booking_id)
        if booking is None:
            continue

        active_statuses = {BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS}
        if booking.booking_status not in active_statuses:
            continue

        if booking.scheduled_date != event_date:
            continue

        # Check time overlap
        b_start = booking.scheduled_start_time
        b_end = booking.scheduled_end_time
        if b_start is None or b_end is None:
            # No time precision — treat the whole day as occupied
            raise VendorNotAvailableError(
                f"Vendor {vendor_id} already has a booking on {event_date}."
            )

        # Overlap: not (end <= b_start or start >= b_end)
        if not (end_time <= b_start or start_time >= b_end):
            raise VendorNotAvailableError(
                f"Vendor {vendor_id} is unavailable on {event_date} "
                f"between {start_time} and {end_time}."
            )


async def validate_package_available(
    package_id: UUID,
    event_date: date,
    uow: UnitOfWork,
):
    """
    Raise PackageNotFoundError if the package does not exist or is not published,
    or if no availability slot is open for event_date. Returns the Package on success.
    """
    from app.services.packages.exceptions import PackageNotPublishedError
    from app.services.packages.helpers import is_package_available_on_date

    package = await uow.packages.packages.get_by_id(package_id)
    if package is None:
        raise PackageNotFoundError(str(package_id))

    # Check active/published status
    from app.models.enums import PackageStatus
    if package.status not in (PackageStatus.ACTIVE,):
        raise PackageNotPublishedError(
            f"Package {package_id} is not active/published."
        )

    slots = await uow.packages.availability.find_by_package(package_id)
    if slots and not is_package_available_on_date(slots, event_date):
        from app.services.exceptions import BusinessRuleError
        raise BusinessRuleError(
            f"Package {package_id} has no available slots on {event_date}."
        )

    return package
