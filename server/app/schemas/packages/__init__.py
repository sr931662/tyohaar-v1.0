"""
Public API for the packages schema package.

Import from here in routers and service layers to avoid deep module paths.
Every symbol defined across the 7 sub-modules is re-exported here.
"""

from __future__ import annotations

# ── common ─────────────────────────────────────────────────────────────────────
from app.schemas.packages.common import (
    PriceTierSchema,
    Currency,
    PackagePricingType,
    PackageStatus,
)

# ── create ─────────────────────────────────────────────────────────────────────
from app.schemas.packages.create import (
    PackageCreate,
    PackageCategoryCreate,
    PackageItemCreate,
    PackageGalleryCreate,
    PackageItemImageCreate,
    PackagePricingCreate,
    PackageDiscountCreate,
    PackageReviewCreate,
    PackageFAQCreate,
    PackageAvailabilityCreate,
)

# ── update ─────────────────────────────────────────────────────────────────────
from app.schemas.packages.update import (
    PackageUpdate,
    PackageCategoryUpdate,
    PackageItemUpdate,
    PackagePricingUpdate,
    PackageDiscountUpdate,
    PackageReviewUpdate,
    PackageFAQUpdate,
    PackageAvailabilityUpdate,
)

# ── response ───────────────────────────────────────────────────────────────────
from app.schemas.packages.response import (
    PackageCategoryResponse,
    PackageResponse,
    PackageItemResponse,
    PackageItemImageResponse,
    PackageGalleryResponse,
    PackagePricingResponse,
    PackageDiscountResponse,
    PackageReviewResponse,
    PackageFAQResponse,
    PackageAvailabilityResponse,
    PackageDetailResponse,
)

# ── filters ────────────────────────────────────────────────────────────────────
from app.schemas.packages.filters import (
    PackageFilters,
    PackageCategoryFilters,
    PackageAvailabilityFilters,
    PackageReviewFilters,
)

# ── pagination ─────────────────────────────────────────────────────────────────
from app.schemas.packages.pagination import (
    PackagePage,
    PackageCategoryPage,
    PackageReviewPage,
    PackageCategoryOffsetPage,
)

# ── internal ───────────────────────────────────────────────────────────────────
from app.schemas.packages.internal import (
    PackageInternal,
    PackageAdminStats,
)

__all__ = [
    # common
    "PriceTierSchema",
    "Currency",
    "PackagePricingType",
    "PackageStatus",
    # create
    "PackageCreate",
    "PackageCategoryCreate",
    "PackageItemCreate",
    "PackageGalleryCreate",
    "PackageItemImageCreate",
    "PackagePricingCreate",
    "PackageDiscountCreate",
    "PackageReviewCreate",
    "PackageFAQCreate",
    "PackageAvailabilityCreate",
    # update
    "PackageUpdate",
    "PackageCategoryUpdate",
    "PackageItemUpdate",
    "PackagePricingUpdate",
    "PackageDiscountUpdate",
    "PackageReviewUpdate",
    "PackageFAQUpdate",
    "PackageAvailabilityUpdate",
    # response
    "PackageCategoryResponse",
    "PackageResponse",
    "PackageItemResponse",
    "PackageItemImageResponse",
    "PackageGalleryResponse",
    "PackagePricingResponse",
    "PackageDiscountResponse",
    "PackageReviewResponse",
    "PackageFAQResponse",
    "PackageAvailabilityResponse",
    "PackageDetailResponse",
    # filters
    "PackageFilters",
    "PackageCategoryFilters",
    "PackageAvailabilityFilters",
    "PackageReviewFilters",
    # pagination
    "PackagePage",
    "PackageCategoryPage",
    "PackageReviewPage",
    "PackageCategoryOffsetPage",
    # internal
    "PackageInternal",
    "PackageAdminStats",
]
