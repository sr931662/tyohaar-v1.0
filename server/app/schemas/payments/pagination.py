"""
Pagination response wrappers for the payments domain.

All page types extend CursorPage[T] for keyset pagination or
OffsetPage[T] for admin dashboards requiring total-count display.
"""

from __future__ import annotations

from app.schemas.base import CursorPage, OffsetPage
from app.schemas.payments.response import (
    CouponResponse,
    PaymentResponse,
    RefundResponse,
)


__all__ = [
    "PaymentPage",
    "RefundPage",
    "CouponPage",
    "PaymentOffsetPage",
    "RefundOffsetPage",
]


class PaymentPage(CursorPage[PaymentResponse]):
    """
    Cursor-paginated list of Payment records.

    Used on the customer payment history screen and admin finance dashboard.
    next_cursor encodes (created_at, id) of the last item on the page.
    """


class RefundPage(CursorPage[RefundResponse]):
    """
    Cursor-paginated list of Refund records.

    Used on the admin refund management screen and customer order history.
    """


class CouponPage(CursorPage[CouponResponse]):
    """
    Cursor-paginated list of Coupon records.

    Used on the admin coupon management screen. Returns CouponResponse
    (authenticated view), not CouponPublicResponse.
    """


class PaymentOffsetPage(OffsetPage[PaymentResponse]):
    """
    Offset-paginated list of Payment records for admin finance reports.

    Supports total-count display and page-number navigation.
    """


class RefundOffsetPage(OffsetPage[RefundResponse]):
    """
    Offset-paginated list of Refund records for admin finance reports.
    """
