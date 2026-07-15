"""
Public API for the bookings schema package.

Import from here in routers and service layers to avoid deep module paths.
Every symbol defined across the 7 sub-modules is re-exported here.
"""

from __future__ import annotations

# ── common ─────────────────────────────────────────────────────────────────────
from app.schemas.bookings.common import (
    BookingFinancialsSchema,
    BookingStatus,
    BookingType,
    CancellationReason,
    Currency,
    InvoiceStatus,
    PaymentStatus,
)

# ── create ─────────────────────────────────────────────────────────────────────
from app.schemas.bookings.create import (
    BookingCreate,
    BookingCancellationCreate,
    BookingRescheduleCreate,
)

# ── update ─────────────────────────────────────────────────────────────────────
from app.schemas.bookings.update import (
    BookingUpdate,
    BookingFinancialsUpdate,
    BookingInvoiceUpdate,
    BookingItemPrepTimeUpdate,
    BookingPSTUpdate,
)

# ── response ───────────────────────────────────────────────────────────────────
from app.schemas.bookings.response import (
    BookingResponse,
    BookingItemResponse,
    BookingCancellationResponse,
    BookingRescheduleResponse,
    BookingStatusHistoryResponse,
    BookingInvoiceResponse,
    BookingDetailResponse,
)

# ── filters ────────────────────────────────────────────────────────────────────
from app.schemas.bookings.filters import (
    BookingFilters,
    BookingStatusHistoryFilters,
    BookingCancellationFilters,
)

# ── pagination ─────────────────────────────────────────────────────────────────
from app.schemas.bookings.pagination import (
    BookingPage,
    BookingStatusHistoryPage,
    BookingInvoicePage,
    BookingCancellationPage,
    BookingOffsetPage,
)

# ── internal ───────────────────────────────────────────────────────────────────
from app.schemas.bookings.internal import (
    BookingInternal,
    BookingAssignmentInternal,
)

__all__ = [
    # common
    "BookingFinancialsSchema",
    "BookingStatus",
    "BookingType",
    "CancellationReason",
    "Currency",
    "InvoiceStatus",
    "PaymentStatus",
    # create
    "BookingCreate",
    "BookingCancellationCreate",
    "BookingRescheduleCreate",
    # update
    "BookingUpdate",
    "BookingFinancialsUpdate",
    "BookingInvoiceUpdate",
    "BookingItemPrepTimeUpdate",
    "BookingPSTUpdate",
    # response
    "BookingResponse",
    "BookingItemResponse",
    "BookingCancellationResponse",
    "BookingRescheduleResponse",
    "BookingStatusHistoryResponse",
    "BookingInvoiceResponse",
    "BookingDetailResponse",
    # filters
    "BookingFilters",
    "BookingStatusHistoryFilters",
    "BookingCancellationFilters",
    # pagination
    "BookingPage",
    "BookingStatusHistoryPage",
    "BookingInvoicePage",
    "BookingCancellationPage",
    "BookingOffsetPage",
    # internal
    "BookingInternal",
    "BookingAssignmentInternal",
]
