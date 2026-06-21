"""
Vendors domain schema package.

Import from here for a single, stable entry point:

    from app.schemas.vendors import VendorCreate, VendorResponse, VendorPage
"""

from __future__ import annotations

# ── common ────────────────────────────────────────────────────────────────────
from app.schemas.vendors.common import (
    TimeSlot,
    WorkingHoursSchema,
    PriceTierSchema,
    SocialLinksSchema,
    # enums
    VendorType,
    VendorStatus,
    VendorVerificationStatus,
    ServiceStatus,
    PackagePricingType,
    VerificationStatus,
    AvailabilityStatus,
    SettlementStatus,
)

# ── create ────────────────────────────────────────────────────────────────────
from app.schemas.vendors.create import (
    VendorCreate,
    VendorProfileCreate,
    VendorServiceCreate,
    VendorDocumentCreate,
    VendorBankAccountCreate,
    VendorReviewCreate,
)

# ── update ────────────────────────────────────────────────────────────────────
from app.schemas.vendors.update import (
    VendorUpdate,
    VendorProfileUpdate,
    VendorServiceUpdate,
    VendorBankAccountUpdate,
    VendorReviewUpdate,
)

# ── response ──────────────────────────────────────────────────────────────────
from app.schemas.vendors.response import (
    VendorResponse,
    VendorProfileResponse,
    VendorServiceResponse,
    VendorCategoryResponse,
    VendorDocumentResponse,
    VendorBankAccountResponse,
    VendorReviewResponse,
)

# ── filters ───────────────────────────────────────────────────────────────────
from app.schemas.vendors.filters import (
    VendorFilters,
    VendorServiceFilters,
    VendorReviewFilters,
)

# ── pagination ────────────────────────────────────────────────────────────────
from app.schemas.vendors.pagination import (
    VendorPage,
    VendorServicePage,
    VendorReviewPage,
)

# ── internal (admin) ──────────────────────────────────────────────────────────
from app.schemas.vendors.internal import (
    VendorInternal,
    VendorBankAccountInternal,
    VendorAdminStats,
)

__all__ = [
    # common
    "TimeSlot",
    "WorkingHoursSchema",
    "PriceTierSchema",
    "SocialLinksSchema",
    "VendorType",
    "VendorStatus",
    "VendorVerificationStatus",
    "ServiceStatus",
    "PackagePricingType",
    "VerificationStatus",
    "AvailabilityStatus",
    "SettlementStatus",
    # create
    "VendorCreate",
    "VendorProfileCreate",
    "VendorServiceCreate",
    "VendorDocumentCreate",
    "VendorBankAccountCreate",
    "VendorReviewCreate",
    # update
    "VendorUpdate",
    "VendorProfileUpdate",
    "VendorServiceUpdate",
    "VendorBankAccountUpdate",
    "VendorReviewUpdate",
    # response
    "VendorResponse",
    "VendorProfileResponse",
    "VendorServiceResponse",
    "VendorCategoryResponse",
    "VendorDocumentResponse",
    "VendorBankAccountResponse",
    "VendorReviewResponse",
    # filters
    "VendorFilters",
    "VendorServiceFilters",
    "VendorReviewFilters",
    # pagination
    "VendorPage",
    "VendorServicePage",
    "VendorReviewPage",
    # internal
    "VendorInternal",
    "VendorBankAccountInternal",
    "VendorAdminStats",
]
