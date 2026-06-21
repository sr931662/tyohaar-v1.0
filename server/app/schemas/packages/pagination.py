"""
Pagination response wrappers for the packages domain.

All page types are specialisations of the generic CursorPage[T] from
app.schemas.base, providing strongly-typed item lists and consistent
cursor-based pagination across package endpoints.
"""

from __future__ import annotations

from app.schemas.base import CursorPage, OffsetPage
from app.schemas.packages.response import (
    PackageCategoryResponse,
    PackageResponse,
    PackageReviewResponse,
)


__all__ = [
    "PackagePage",
    "PackageCategoryPage",
    "PackageReviewPage",
    "PackageCategoryOffsetPage",
]


class PackagePage(CursorPage[PackageResponse]):
    """
    Cursor-paginated list of Package records.

    Use for the public package listing endpoint. next_cursor encodes
    (created_at, id) of the last item on the current page.
    """


class PackageCategoryPage(CursorPage[PackageCategoryResponse]):
    """Cursor-paginated list of PackageCategory records."""


class PackageReviewPage(CursorPage[PackageReviewResponse]):
    """
    Cursor-paginated list of PackageReview records.

    The package detail page streams reviews in chronological order.
    """


class PackageCategoryOffsetPage(OffsetPage[PackageCategoryResponse]):
    """
    Offset-paginated list of PackageCategory records.

    Used in the admin dashboard where total-count display is required.
    """
