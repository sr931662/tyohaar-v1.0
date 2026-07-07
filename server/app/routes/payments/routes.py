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
    PaymentResponse,
    RefundResponse,
)
from app.services.payments.service import (
    InvoiceResponse,
    PaymentInitResponse,
    PaymentSplitResponse,
    PaymentTransactionResponse,
    WalletTopupInitResponse,
)

router = APIRouter(prefix="/payments", tags=["Payments"])

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
    "/coupons/{coupon_id}",
    ctrl.deactivate_coupon,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Deactivate Coupon (Admin)",
    description="Deactivate a coupon so it can no longer be redeemed. Admin access required.",
    operation_id="payments_deactivate_coupon",
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
    "/bookings/{booking_id}/wallet",
    ctrl.initiate_wallet_payment,
    methods=["POST"],
    response_model=SuccessResponse[PaymentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Pay with Wallet",
    description="Debit the user's wallet balance to pay for a booking. Pass `amount` as a query parameter.",
    operation_id="payments_initiate_wallet_payment",
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

# ── Wallet top-up ─────────────────────────────────────────────────────────────

router.add_api_route(
    "/wallet/topup",
    ctrl.initiate_wallet_topup,
    methods=["POST"],
    response_model=SuccessResponse[WalletTopupInitResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Wallet Top-up",
    description="Create a gateway order to add funds to the authenticated user's wallet. Pass `amount` as a query parameter.",
    operation_id="payments_initiate_wallet_topup",
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
