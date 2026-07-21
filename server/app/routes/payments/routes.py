"""
Payments Routes — payment initiation, verification, refunds, coupons, splits, and invoices.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.payments import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.payments.response import (
    CouponResponse,
    CouponValidationResponse,
    DiscountAnalyticsOverview,
    DiscountEvaluationResponse,
    PaymentResponse,
    RefundResponse,
)
from app.services.payments.service import (
    InvoiceResponse,
    PaymentGatewayConfig,
    PaymentInitResponse,
    PaymentSplitResponse,
    PaymentTransactionResponse,
    VendorEarningsSummary,
)

router = APIRouter(prefix="/payments", tags=["Payments"])

# ── Gateway config (public, static — must precede /{payment_id}) ────────────

router.add_api_route(
    "/config",
    ctrl.get_gateway_config,
    methods=["GET"],
    response_model=SuccessResponse[PaymentGatewayConfig],
    status_code=status.HTTP_200_OK,
    summary="Get Payment Gateway Config",
    description="Public, non-secret gateway config (key_id only) the client needs to open checkout.",
    operation_id="payments_get_gateway_config",
)

# ── Coupons (static — must precede /{payment_id}) ────────────────────────────

router.add_api_route(
    "/coupons/validate",
    ctrl.validate_coupon,
    methods=["GET"],
    response_model=SuccessResponse[CouponValidationResponse],
    status_code=status.HTTP_200_OK,
    summary="Validate Coupon",
    description="Validate a coupon code against a booking and amount. Returns discount details.",
    operation_id="payments_validate_coupon",
)

router.add_api_route(
    "/coupons",
    ctrl.list_active_coupons,
    methods=["GET"],
    response_model=SuccessResponse[list[CouponResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Active Coupons",
    description="Return all currently active coupons available to the authenticated user.",
    operation_id="payments_list_active_coupons",
)

router.add_api_route(
    "/coupons",
    ctrl.create_coupon,
    methods=["POST"],
    response_model=SuccessResponse[CouponResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Coupon (Admin)",
    description="Create a new discount coupon. Admin access required.",
    operation_id="payments_create_coupon",
)

router.add_api_route(
    "/coupons/preview",
    ctrl.preview_discount,
    methods=["POST"],
    response_model=SuccessResponse[DiscountEvaluationResponse],
    status_code=status.HTTP_200_OK,
    summary="Preview Discount Evaluation",
    description=(
        "Evaluate every applicable discount (automatic + an optional coupon "
        "code) for a basket and return the resolved, itemized result — the "
        "same evaluation create_booking uses, exposed read-only for "
        "checkout-time price display. All calculation happens server-side."
    ),
    operation_id="payments_preview_discount",
)

router.add_api_route(
    "/coupons/admin",
    ctrl.list_coupons_admin,
    methods=["GET"],
    response_model=CursorPaginatedResponse[CouponResponse],
    status_code=status.HTTP_200_OK,
    summary="List All Discounts (Admin)",
    description="Return every discount regardless of status (draft/scheduled/active/paused/expired/archived). Admin access required.",
    operation_id="payments_list_coupons_admin",
)

router.add_api_route(
    "/coupons/analytics",
    ctrl.get_discount_analytics,
    methods=["GET"],
    response_model=SuccessResponse[DiscountAnalyticsOverview],
    status_code=status.HTTP_200_OK,
    summary="Discount Analytics Overview (Admin)",
    description="Status breakdown, usage counts, revenue generated/lost, conversion rate, and top performing discounts. Admin access required.",
    operation_id="payments_get_discount_analytics",
)

router.add_api_route(
    "/coupons/{coupon_id}",
    ctrl.update_coupon,
    methods=["PATCH"],
    response_model=SuccessResponse[CouponResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Discount (Admin)",
    description="Partially update a discount's configuration. Admin access required.",
    operation_id="payments_update_coupon",
)

router.add_api_route(
    "/coupons/{coupon_id}",
    ctrl.deactivate_coupon,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Deactivate Coupon (Admin)",
    description="Deactivate a coupon so it can no longer be redeemed. Admin access required.",
    operation_id="payments_deactivate_coupon",
)

router.add_api_route(
    "/coupons/{coupon_id}/duplicate",
    ctrl.duplicate_coupon,
    methods=["POST"],
    response_model=SuccessResponse[CouponResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate Discount (Admin)",
    description="Clone a discount as a new unpublished draft. Admin access required.",
    operation_id="payments_duplicate_coupon",
)

router.add_api_route(
    "/coupons/{coupon_id}/archive",
    ctrl.archive_coupon,
    methods=["POST"],
    response_model=SuccessResponse[CouponResponse],
    status_code=status.HTTP_200_OK,
    summary="Archive Discount (Admin)",
    description="Soft-delete a discount — permanently excluded from evaluation. Admin access required.",
    operation_id="payments_archive_coupon",
)

# ── Invoices (static — must precede /{payment_id}) ───────────────────────────

router.add_api_route(
    "/invoices",
    ctrl.list_invoices,
    methods=["GET"],
    response_model=SuccessResponse[list[InvoiceResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Invoices",
    description="Return invoices for a given entity. Pass `entity_id` and `entity_type` as query parameters.",
    operation_id="payments_list_invoices",
)

router.add_api_route(
    "/invoices/{invoice_id}",
    ctrl.get_invoice,
    methods=["GET"],
    response_model=SuccessResponse[InvoiceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Invoice",
    description="Return a single invoice by ID.",
    operation_id="payments_get_invoice",
)

# ── Booking-scoped payment initiation ────────────────────────────────────────

router.add_api_route(
    "/bookings/{booking_id}",
    ctrl.initiate_payment,
    methods=["POST"],
    response_model=SuccessResponse[PaymentInitResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Payment",
    description="Initiate a gateway payment for a booking. Returns the gateway order/session details.",
    operation_id="payments_initiate_payment",
)

router.add_api_route(
    "/bookings/{booking_id}/refunds",
    ctrl.list_refunds,
    methods=["GET"],
    response_model=SuccessResponse[list[RefundResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Refunds for Booking",
    description="Return all refund records associated with a booking.",
    operation_id="payments_list_refunds",
)

# ── Vendor earnings ───────────────────────────────────────────────────────────

router.add_api_route(
    "/vendor/earnings",
    ctrl.get_vendor_earnings,
    methods=["GET"],
    response_model=SuccessResponse[VendorEarningsSummary],
    status_code=status.HTTP_200_OK,
    summary="Vendor Earnings",
    description="Razorpay payment analytics scoped to the authenticated vendor's own bookings.",
    operation_id="payments_get_vendor_earnings",
)

# ── Webhooks ──────────────────────────────────────────────────────────────────

router.add_api_route(
    "/webhooks/{gateway}",
    ctrl.handle_webhook,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Payment Gateway Webhook",
    description="Receive and process an inbound webhook from a payment gateway. Signature is verified internally.",
    operation_id="payments_handle_webhook",
)

# ── Payment lifecycle ─────────────────────────────────────────────────────────

router.add_api_route(
    "/{payment_id}/verify",
    ctrl.verify_payment,
    methods=["GET"],
    response_model=SuccessResponse[PaymentResponse],
    status_code=status.HTTP_200_OK,
    summary="Verify Payment",
    description="Verify a payment against the gateway signature. Pass `gateway_payment_id`, `gateway_signature`, and `gateway` as query parameters.",
    operation_id="payments_verify_payment",
)

router.add_api_route(
    "/{payment_id}",
    ctrl.get_payment,
    methods=["GET"],
    response_model=SuccessResponse[PaymentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Payment",
    description="Return a single payment by ID. Customer ownership required.",
    operation_id="payments_get_payment",
)

router.add_api_route(
    "",
    ctrl.list_payments,
    methods=["GET"],
    response_model=CursorPaginatedResponse[PaymentResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Payments",
    description="Return a cursor-paginated list of payments for the authenticated customer.",
    operation_id="payments_list_payments",
)

router.add_api_route(
    "/{payment_id}/transactions",
    ctrl.get_payment_transactions,
    methods=["GET"],
    response_model=SuccessResponse[list[PaymentTransactionResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Payment Transactions",
    description="Return all gateway transaction logs for a payment.",
    operation_id="payments_get_payment_transactions",
)

router.add_api_route(
    "/{payment_id}/refunds",
    ctrl.initiate_refund,
    methods=["POST"],
    response_model=SuccessResponse[RefundResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Refund (Admin)",
    description="Initiate a refund for a payment. Admin access required.",
    operation_id="payments_initiate_refund",
)

router.add_api_route(
    "/{payment_id}/splits",
    ctrl.create_payment_split,
    methods=["POST"],
    response_model=SuccessResponse[PaymentSplitResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Payment Split (Admin)",
    description="Record a payout split for a payment. Admin access required.",
    operation_id="payments_create_payment_split",
)

router.add_api_route(
    "/{payment_id}/splits",
    ctrl.list_payment_splits,
    methods=["GET"],
    response_model=SuccessResponse[list[PaymentSplitResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Payment Splits (Admin)",
    description="Return all split records for a payment. Admin access required.",
    operation_id="payments_list_payment_splits",
)
