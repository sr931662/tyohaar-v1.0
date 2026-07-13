from __future__ import annotations

from app.services.exceptions import (
    BookingConflictError,
    BusinessRuleError,
    NotFoundError,
    PermissionError,
)


class BookingNotFoundError(NotFoundError):
    def __init__(self, booking_id: str | None = None) -> None:
        super().__init__("Booking", booking_id)


class BookingOwnershipError(PermissionError):
    default_message = "You do not own this booking."


class BookingStatusTransitionError(BusinessRuleError):
    def __init__(self, current: str, requested: str) -> None:
        super().__init__(
            f"Cannot transition booking from '{current}' to '{requested}'.",
            {"current_status": current, "requested_status": requested},
        )


class BookingCutoffError(BusinessRuleError):
    default_message = (
        "Bookings must be made at least 24 hours before the scheduled event."
    )


class BookingCancellationWindowError(BusinessRuleError):
    default_message = (
        "Cancellations must be requested at least 48 hours before the scheduled event."
    )


class BookingRescheduleWindowError(BusinessRuleError):
    default_message = (
        "Reschedules must be requested at least 48 hours before the scheduled event."
    )


class VendorNotAvailableError(BookingConflictError):
    default_message = "The vendor is not available for the requested date and time."


class BookingItemLimitError(BusinessRuleError):
    default_message = "Booking has reached the maximum number of items."


class CelebrationRequiredError(BusinessRuleError):
    default_message = (
        "Could not determine which celebration this booking belongs to. "
        "Pass celebration_id explicitly, or occasion_id so one can be created."
    )


class AssignmentNotFoundError(NotFoundError):
    def __init__(self, assignment_id: str | None = None) -> None:
        super().__init__("BookingAssignment", assignment_id)


class VendorAssignmentOwnershipError(PermissionError):
    default_message = "You are not assigned to this booking item."
