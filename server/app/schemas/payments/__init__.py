"""
Public API for the payments schema package.

Import from here in routers and service layers to avoid deep module paths.
Every symbol defined across the 7 sub-modules is re-exported here.
"""

from __future__ import annotations

# ── common ─────────────────────────────────────────────────────────────────────
from app.schemas.payments.common import (
    PaymentGatewayEnum,
    CouponValidationResult,
    CouponApplicability,
    CouponType,
    Currency,
    PaymentMethod,
    PaymentStatus,
    RefundStatus,
    TransactionType,
)

# ── create ─────────────────────────────────────────────────────────────────────
from app.schemas.payments.create import (
    PaymentCreate,
    RefundCreate,
    CouponCreate,
    CouponValidateRequest,
    DiscountPreviewRequest,
)

# ── update ─────────────────────────────────────────────────────────────────────
from app.schemas.payments.update import (
    PaymentUpdate,
    RefundUpdate,
    CouponUpdate,
)

# ── response ───────────────────────────────────────────────────────────────────
from app.schemas.payments.response import (
    PaymentResponse,
    RefundResponse,
    CouponResponse,
    CouponPublicResponse,
    CouponValidationResponse,
    AppliedDiscountItem,
    DiscountEvaluationResponse,
    PaymentWebhookResponse,
)

# ── filters ────────────────────────────────────────────────────────────────────
from app.schemas.payments.filters import (
    PaymentFilters,
    RefundFilters,
    CouponFilters,
    PaymentWebhookFilters,
)

# ── pagination ─────────────────────────────────────────────────────────────────
from app.schemas.payments.pagination import (
    PaymentPage,
    RefundPage,
    CouponPage,
    PaymentOffsetPage,
    RefundOffsetPage,
)

# ── internal ───────────────────────────────────────────────────────────────────
from app.schemas.payments.internal import (
    PaymentInternal,
    PaymentWebhookInternal,
    CouponInternal,
)

__all__ = [
    # common
    "PaymentGatewayEnum",
    "CouponValidationResult",
    "CouponApplicability",
    "CouponType",
    "Currency",
    "PaymentMethod",
    "PaymentStatus",
    "RefundStatus",
    "TransactionType",
    # create
    "PaymentCreate",
    "RefundCreate",
    "CouponCreate",
    "CouponValidateRequest",
    "DiscountPreviewRequest",
    # update
    "PaymentUpdate",
    "RefundUpdate",
    "CouponUpdate",
    # response
    "PaymentResponse",
    "RefundResponse",
    "CouponResponse",
    "CouponPublicResponse",
    "CouponValidationResponse",
    "AppliedDiscountItem",
    "DiscountEvaluationResponse",
    "PaymentWebhookResponse",
    # filters
    "PaymentFilters",
    "RefundFilters",
    "CouponFilters",
    "PaymentWebhookFilters",
    # pagination
    "PaymentPage",
    "RefundPage",
    "CouponPage",
    "PaymentOffsetPage",
    "RefundOffsetPage",
    # internal
    "PaymentInternal",
    "PaymentWebhookInternal",
    "CouponInternal",
]
