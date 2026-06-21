"""
Pagination response wrappers for the bookings domain.

All page types extend CursorPage[T] from app.schemas.base for
cursor-based keyset pagination, or OffsetPage[T] for admin dashboards.
"""

from __future__ import annotations

from app.schemas.base import CursorPage, OffsetPage
from app.schemas.bookings.response import (
    BookingResponse,
    BookingStatusHistoryResponse,
    BookingInvoiceResponse,
    BookingCancellationResponse,
)


__all__ = [
    "BookingPage",
    "BookingStatusHistoryPage",
    "BookingInvoicePage",
    "BookingCancellationPage",
    "BookingOffsetPage",
]


class BookingPage(CursorPage[BookingResponse]):
    """
    Cursor-paginated list of Booking records.

    Used on the customer 'My Bookings' screen and admin booking list.
    next_cursor encodes (created_at, id) of the last item on the page.
    """


class BookingStatusHistoryPage(CursorPage[BookingStatusHistoryResponse]):
    """
    Cursor-paginated list of BookingStatusHistory entries.

    Used when rendering the timeline of status transitions on a
    booking detail page.
    """


class BookingInvoicePage(CursorPage[BookingInvoiceResponse]):
    """Cursor-paginated list of BookingInvoice records."""


class BookingCancellationPage(CursorPage[BookingCancellationResponse]):
    """Cursor-paginated list of BookingCancellation records (admin only)."""


class BookingOffsetPage(OffsetPage[BookingResponse]):
    """
    Offset-paginated list of Booking records for the admin dashboard.

    Supports total-count display required by admin table components.
    """
