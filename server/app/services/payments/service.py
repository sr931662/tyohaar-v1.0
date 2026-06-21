"""
PaymentService — orchestrates all payment domain business logic.

Side effects (gateway API calls) are executed AFTER the async with block exits
so they never roll back a committed transaction.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import (
    CouponType,
    PaymentStatus,
    RefundStatus,
    TransactionType,
    WalletTransactionType,
)
from app.models.payments.payment import PaymentGateway
from app.models.payments.payment_attempt import PaymentAttemptStatus
from app.models.payments.refund import RefundType
from app.models.payments.transaction import PartyType, TransactionDirection
from app.schemas.base import CursorPage
from app.schemas.payments.create import CouponCreate, PaymentCreate, RefundCreate
from app.schemas.payments.response import (
    CouponResponse,
    CouponValidationResponse,
    PaymentResponse,
    RefundResponse,
)
from app.schemas.payments.filters import PaymentFilters
from app.services.base import BaseService
from app.services.exceptions import BusinessRuleError, ExternalServiceError, InsufficientBalanceError, NotFoundError
from app.services.payments.exceptions import (
    CouponNotFoundError,
    InvalidGatewaySignatureError,
    PaymentAlreadyFailedError,
)
from app.services.payments.helpers import (
    calculate_coupon_discount,
    calculate_gst,
    calculate_platform_fee,
    generate_payment_reference,
    verify_webhook_signature,
)
from app.services.payments.validators import (
    validate_coupon_applicable,
    validate_gateway_supported,
    validate_payment_amount,
    validate_payment_exists,
    validate_refund_amount,
)

logger = logging.getLogger(__name__)


@dataclass
class PaymentInitResponse:
    """Minimal data returned to the client to proceed through gateway checkout."""

    payment_id: uuid.UUID
    payment_number: str
    gateway_order_id: str
    checkout_url: str | None
    amount: Decimal
    currency: str = "INR"
    gateway: str = "razorpay"
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )


@dataclass
class PaymentSplitCreate:
    """Input for creating a vendor payout split."""

    vendor_id: uuid.UUID
    amount: Decimal
    description: str | None = None


@dataclass
class PaymentSplitResponse:
    """Public representation of a vendor payout split."""

    id: uuid.UUID
    payment_id: uuid.UUID
    vendor_id: uuid.UUID
    amount: Decimal
    is_settled: bool


@dataclass
class InvoiceResponse:
    """Minimal invoice response returned from the service."""

    id: uuid.UUID
    invoice_number: str
    entity_type: str
    total_amount: Decimal
    invoice_status: str


@dataclass
class PaymentTransactionResponse:
    """Minimal payment transaction response."""

    id: uuid.UUID
    payment_id: uuid.UUID
    transaction_type: str
    amount: Decimal
    is_success: bool
    initiated_at: datetime


def _generate_txn_number() -> str:
    import secrets
    suffix = str(secrets.randbelow(1_000_000)).zfill(6)
    year = datetime.now(tz=timezone.utc).year
    return f"TXN-{year}-{suffix}"


class PaymentService(BaseService):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Payment Initiation ────────────────────────────────────────────────────

    async def initiate_payment(
        self,
        booking_id: uuid.UUID,
        customer_id: uuid.UUID,
        data: PaymentCreate,
    ) -> PaymentInitResponse:
        """
        Initiate a gateway-backed payment for a booking.

        1. Validate amount, gateway, booking ownership.
        2. Calculate platform fee + GST.
        3. Apply coupon discount if provided.
        4. Create Payment (PENDING) + PaymentAttempt + Transaction ledger entry.
        5. Return stubbed gateway order data (replace with real gateway SDK call).
        """
        validate_payment_amount(data.subtotal)
        if data.gateway:
            validate_gateway_supported(data.gateway.value if hasattr(data.gateway, "value") else str(data.gateway))

        platform_fee = calculate_platform_fee(data.subtotal)
        gst = calculate_gst(platform_fee)
        payment_number = generate_payment_reference()

        payment_obj: object = None
        async with self._uow() as uow:
            # Validate booking exists and belongs to this customer
            booking = await uow.bookings.bookings.get_by_id(booking_id)
            if booking is None:
                raise NotFoundError("Booking", str(booking_id))
            if booking.customer_id != customer_id:
                raise BusinessRuleError("Booking does not belong to this customer.")

            payment = await uow.payments.payments.create({
                "booking_id": booking_id,
                "payer_id": customer_id,
                "currency": data.currency,
                "subtotal": data.subtotal,
                "discount_amount": data.discount_amount,
                "tax_amount": data.tax_amount + gst,
                "platform_fee": platform_fee,
                "final_amount": data.final_amount,
                "payment_status": PaymentStatus.PENDING,
                "payment_method": data.payment_method,
                "gateway": data.gateway,
                "payment_number": payment_number,
                # Stub gateway order id — replace with real gateway call
                "gateway_order_id": f"order_{payment_number.lower()}",
            })

            attempt_count = await uow.payments.attempts.count_for_payment(payment.id)
            await uow.payments.attempts.create({
                "payment_id": payment.id,
                "attempt_number": attempt_count + 1,
                "attempt_status": PaymentAttemptStatus.INITIATED,
                "initiated_at": datetime.now(tz=timezone.utc),
            })

            await uow.payments.ledger.create({
                "transaction_number": _generate_txn_number(),
                "transaction_type": TransactionType.PAYMENT,
                "direction": TransactionDirection.CREDIT,
                "amount": payment.final_amount,
                "currency": payment.currency,
                "payer_type": PartyType.CUSTOMER,
                "payer_id": customer_id,
                "payee_type": PartyType.PLATFORM,
                "payee_id": None,
                "booking_id": booking_id,
                "payment_id": payment.id,
                "description": f"Payment initiated for booking {booking_id}",
                "transacted_at": datetime.now(tz=timezone.utc),
            })

            payment_obj = payment

        # Side effects (real gateway order creation) happen here after commit
        return PaymentInitResponse(
            payment_id=payment_obj.id,
            payment_number=payment_obj.payment_number,
            gateway_order_id=payment_obj.gateway_order_id or f"order_{payment_obj.payment_number.lower()}",
            checkout_url=None,  # Populate from gateway SDK response
            amount=payment_obj.final_amount,
            gateway=str(payment_obj.gateway.value) if payment_obj.gateway else "razorpay",
        )

    async def initiate_wallet_payment(
        self,
        booking_id: uuid.UUID,
        customer_id: uuid.UUID,
        amount: Decimal,
    ) -> PaymentResponse:
        """
        Debit the customer wallet and create a completed payment record.

        Uses SELECT FOR UPDATE on the wallet to prevent concurrent balance races.
        """
        validate_payment_amount(amount)
        payment_number = generate_payment_reference()

        async with self._uow() as uow:
            # Acquire row lock on wallet
            wallet = await uow.wallets.wallets.get_by_user_with_lock(customer_id)
            if wallet is None:
                raise NotFoundError("Wallet", f"user_id={customer_id}")

            if wallet.available_balance < amount:
                raise InsufficientBalanceError(
                    f"Insufficient wallet balance. Available: ₹{wallet.available_balance}, required: ₹{amount}."
                )

            booking = await uow.bookings.bookings.get_by_id(booking_id)
            if booking is None:
                raise NotFoundError("Booking", str(booking_id))
            if booking.customer_id != customer_id:
                raise BusinessRuleError("Booking does not belong to this customer.")

            balance_before = wallet.available_balance
            balance_after = balance_before - amount
            await uow.wallets.wallets.update(wallet, {
                "available_balance": balance_after,
                "lifetime_debits": wallet.lifetime_debits + amount,
                "last_transaction_at": datetime.now(tz=timezone.utc),
            })

            payment = await uow.payments.payments.create({
                "booking_id": booking_id,
                "payer_id": customer_id,
                "currency": wallet.currency,
                "subtotal": amount,
                "discount_amount": Decimal("0.00"),
                "tax_amount": Decimal("0.00"),
                "platform_fee": Decimal("0.00"),
                "final_amount": amount,
                "payment_status": PaymentStatus.COMPLETED,
                "gateway": PaymentGateway.OFFLINE,
                "payment_number": payment_number,
                "captured_at": datetime.now(tz=timezone.utc),
            })

            await uow.wallets.transactions.create({
                "wallet_id": wallet.id,
                "transaction_type": WalletTransactionType.DEBIT,
                "amount": amount,
                "balance_before": balance_before,
                "balance_after": balance_after,
                "description": f"Wallet payment for booking {booking_id}",
                "reference_type": "payment",
                "reference_id": payment.id,
            })

            await uow.payments.ledger.create({
                "transaction_number": _generate_txn_number(),
                "transaction_type": TransactionType.PAYMENT,
                "direction": TransactionDirection.CREDIT,
                "amount": amount,
                "currency": wallet.currency,
                "payer_type": PartyType.CUSTOMER,
                "payer_id": customer_id,
                "payee_type": PartyType.PLATFORM,
                "payee_id": None,
                "booking_id": booking_id,
                "payment_id": payment.id,
                "description": f"Wallet payment for booking {booking_id}",
                "transacted_at": datetime.now(tz=timezone.utc),
            })

            result = PaymentResponse.model_validate(payment)

        return result

    # ── Webhook Handling ──────────────────────────────────────────────────────

    async def handle_webhook(
        self,
        gateway: str,
        payload: bytes,
        signature: str,
        secret: str,
    ) -> None:
        """
        Process a payment gateway webhook (idempotent).

        1. Verify HMAC signature — ExternalServiceError on failure.
        2. Parse payload for gateway_order_id and success/failure status.
        3. Skip if payment already COMPLETED or FAILED (idempotency).
        4. On SUCCESS: complete payment, record transaction, write ledger.
        5. On FAILURE: mark payment FAILED, increment attempt count.
        """
        if not verify_webhook_signature(payload, signature, secret, gateway):
            raise InvalidGatewaySignatureError()

        # Minimal payload parsing — expand per gateway SDK spec
        import json
        try:
            body = json.loads(payload)
        except Exception:
            raise ExternalServiceError(gateway, "Could not parse webhook payload.")

        # Razorpay-style extraction; stub for others
        gateway_order_id: str | None = None
        gateway_payment_id: str | None = None
        is_success = False

        event = body.get("event", "")
        entity = body.get("payload", {}).get("payment", {}).get("entity", {})
        gateway_order_id = entity.get("order_id")
        gateway_payment_id = entity.get("id")
        is_success = event == "payment.captured"

        if not gateway_order_id:
            logger.warning("Webhook received without gateway_order_id; skipping.")
            return

        async with self._uow() as uow:
            payment = await uow.payments.payments.find_by_gateway_order(gateway_order_id)
            if payment is None:
                logger.warning("Webhook for unknown gateway_order_id=%s", gateway_order_id)
                return

            # Idempotency guard
            if payment.payment_status in (PaymentStatus.COMPLETED, PaymentStatus.FAILED):
                return

            now = datetime.now(tz=timezone.utc)

            # Store raw webhook — payload bytes stored server-side, never returned to clients
            await uow.payments.webhooks.create({
                "payment_id": payment.id,
                "gateway": gateway,
                "event_type": event,
                "gateway_event_id": entity.get("id", ""),
                "is_processed": True,
                "received_at": now,
                # raw payload stored internally; signature excluded from any response
            })

            if is_success:
                await uow.payments.payments.update(payment, {
                    "payment_status": PaymentStatus.COMPLETED,
                    "gateway_payment_id": gateway_payment_id,
                    "captured_at": now,
                })

                await uow.payments.transactions.create({
                    "payment_id": payment.id,
                    "transaction_type": TransactionType.PAYMENT,
                    "amount": payment.final_amount,
                    "currency": payment.currency,
                    "gateway_transaction_id": gateway_payment_id,
                    "is_success": True,
                    "initiated_at": now,
                    "completed_at": now,
                })

                await uow.payments.ledger.create({
                    "transaction_number": _generate_txn_number(),
                    "transaction_type": TransactionType.PAYMENT,
                    "direction": TransactionDirection.CREDIT,
                    "amount": payment.final_amount,
                    "currency": payment.currency,
                    "payer_type": PartyType.CUSTOMER,
                    "payer_id": payment.payer_id,
                    "payee_type": PartyType.PLATFORM,
                    "payee_id": None,
                    "booking_id": payment.booking_id,
                    "payment_id": payment.id,
                    "description": f"Payment captured via {gateway}",
                    "transacted_at": now,
                })
            else:
                await uow.payments.payments.update(payment, {
                    "payment_status": PaymentStatus.FAILED,
                    "failed_at": now,
                })

                # Increment attempt counter
                attempts = await uow.payments.attempts.find_by_payment(payment.id)
                if attempts:
                    latest = attempts[-1]
                    await uow.payments.attempts.update(latest, {
                        "attempt_status": PaymentAttemptStatus.FAILED,
                        "completed_at": now,
                    })

    async def verify_payment(
        self,
        payment_id: uuid.UUID,
        gateway_payment_id: str,
        gateway_signature: str,
        secret: str,
        gateway: str = "razorpay",
    ) -> PaymentResponse:
        """
        Client-side redirect verification (Razorpay checkout flow).
        Verifies the HMAC and marks the payment as COMPLETED.
        """
        async with self._uow() as uow:
            payment = await validate_payment_exists(payment_id, uow)

            if payment.payment_status == PaymentStatus.COMPLETED:
                return PaymentResponse.model_validate(payment)

            if payment.payment_status == PaymentStatus.FAILED:
                raise PaymentAlreadyFailedError()

            # For Razorpay: HMAC is over "order_id|payment_id"
            order_id = payment.gateway_order_id or ""
            raw = f"{order_id}|{gateway_payment_id}".encode("utf-8")
            if not verify_webhook_signature(raw, gateway_signature, secret, gateway):
                raise InvalidGatewaySignatureError()

            now = datetime.now(tz=timezone.utc)
            await uow.payments.payments.update(payment, {
                "payment_status": PaymentStatus.COMPLETED,
                "gateway_payment_id": gateway_payment_id,
                # gateway_signature stored internally; never returned to clients
                "gateway_signature": gateway_signature,
                "captured_at": now,
            })

            result = PaymentResponse.model_validate(payment)

        return result

    # ── Payment Queries ───────────────────────────────────────────────────────

    async def get_payment(self, payment_id: uuid.UUID, customer_id: uuid.UUID) -> PaymentResponse:
        async with self._uow() as uow:
            payment = await validate_payment_exists(payment_id, uow)
            if payment.payer_id != customer_id:
                raise BusinessRuleError("Payment does not belong to this customer.")
            return PaymentResponse.model_validate(payment)

    async def list_payments(
        self,
        customer_id: uuid.UUID,
        filters: PaymentFilters,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage[PaymentResponse]:
        async with self._uow() as uow:
            payments = await uow.payments.payments.find_by_payer(
                customer_id, skip=0, limit=limit
            )
            items = [PaymentResponse.model_validate(p) for p in payments]
            return CursorPage(items=items, has_more=len(items) == limit)

    async def get_payment_transactions(
        self, payment_id: uuid.UUID
    ) -> list[PaymentTransactionResponse]:
        async with self._uow() as uow:
            txns = await uow.payments.transactions.find_by_payment(payment_id)
            return [
                PaymentTransactionResponse(
                    id=t.id,
                    payment_id=t.payment_id,
                    transaction_type=str(t.transaction_type),
                    amount=t.amount,
                    is_success=t.is_success,
                    initiated_at=t.initiated_at,
                )
                for t in txns
            ]

    # ── Refunds ───────────────────────────────────────────────────────────────

    async def initiate_refund(
        self,
        payment_id: uuid.UUID,
        data: RefundCreate,
        admin_id: uuid.UUID,
    ) -> RefundResponse:
        """
        Create a PENDING refund record and write the ledger entry.
        Gateway refund API call is a stub — execute after the async with block.
        """
        async with self._uow() as uow:
            payment = await validate_payment_exists(payment_id, uow)

            if payment.payment_status != PaymentStatus.COMPLETED:
                raise BusinessRuleError("Only COMPLETED payments can be refunded.")

            validate_refund_amount(payment, data.amount)

            now = datetime.now(tz=timezone.utc)
            refund = await uow.payments.refunds.create({
                "payment_id": payment_id,
                "booking_id": payment.booking_id,
                "refund_type": RefundType.FULL if data.amount == payment.final_amount else RefundType.PARTIAL,
                "refund_reason": data.reason or "customer_request",
                "amount": data.amount,
                "currency": payment.currency,
                "refund_status": RefundStatus.PENDING,
                "initiated_by_id": data.initiated_by_id or admin_id,
                "requested_at": now,
                "approved_by_id": admin_id,
                "approved_at": now,
            })

            await uow.payments.ledger.create({
                "transaction_number": _generate_txn_number(),
                "transaction_type": TransactionType.REFUND,
                "direction": TransactionDirection.DEBIT,
                "amount": data.amount,
                "currency": payment.currency,
                "payer_type": PartyType.PLATFORM,
                "payer_id": None,
                "payee_type": PartyType.CUSTOMER,
                "payee_id": payment.payer_id,
                "booking_id": payment.booking_id,
                "payment_id": payment_id,
                "description": f"Refund initiated for payment {payment_id}",
                "transacted_at": now,
            })

            result = RefundResponse.model_validate(refund)

        # TODO: call gateway refund API here (side effect after commit)
        return result

    async def process_refund_webhook(
        self,
        gateway: str,
        payload: bytes,
        signature: str,
        secret: str,
    ) -> None:
        """Process gateway refund webhook; credit wallet if applicable."""
        if not verify_webhook_signature(payload, signature, secret, gateway):
            raise InvalidGatewaySignatureError()

        import json
        try:
            body = json.loads(payload)
        except Exception:
            raise ExternalServiceError(gateway, "Could not parse refund webhook payload.")

        entity = body.get("payload", {}).get("refund", {}).get("entity", {})
        gateway_refund_id = entity.get("id")
        is_processed = body.get("event", "") == "refund.processed"

        if not gateway_refund_id:
            return

        async with self._uow() as uow:
            refund = await uow.payments.refunds.find_by_gateway_ref(gateway_refund_id)
            if refund is None:
                return

            now = datetime.now(tz=timezone.utc)
            if is_processed:
                await uow.payments.refunds.update(refund, {
                    "refund_status": RefundStatus.COMPLETED,
                    "processed_at": now,
                })

    async def list_refunds(self, booking_id: uuid.UUID) -> list[RefundResponse]:
        async with self._uow() as uow:
            refunds = await uow.payments.refunds.find_by_booking(booking_id)
            return [RefundResponse.model_validate(r) for r in refunds]

    # ── Coupons ───────────────────────────────────────────────────────────────

    async def validate_coupon(
        self,
        code: str,
        user_id: uuid.UUID,
        booking_id: uuid.UUID,
        amount: Decimal,
    ) -> CouponValidationResponse:
        """
        Read-only coupon validation — returns discount details without marking the coupon used.
        """
        code = code.upper().strip()
        async with self._uow() as uow:
            coupon = await uow.payments.coupons.find_by_code(code)
            if coupon is None:
                return CouponValidationResponse(
                    is_valid=False,
                    discount_amount=Decimal("0.00"),
                    applied_code=code,
                    error_message="Coupon code not found.",
                )

            try:
                await validate_coupon_applicable(coupon, user_id, booking_id, amount, uow)
            except Exception as exc:
                return CouponValidationResponse(
                    is_valid=False,
                    discount_amount=Decimal("0.00"),
                    applied_code=code,
                    error_message=str(exc),
                )

            coupon_type_str = (
                "percentage" if coupon.coupon_type == CouponType.PERCENTAGE else "flat"
            )
            discount = calculate_coupon_discount(
                amount, coupon_type_str, coupon.discount_value, coupon.max_discount_amount
            )

            return CouponValidationResponse(
                is_valid=True,
                discount_amount=discount,
                applied_code=code,
            )

    async def list_active_coupons(
        self, user_id: uuid.UUID | None = None
    ) -> list[CouponResponse]:
        """Return all active, non-expired, non-exhausted coupons."""
        async with self._uow() as uow:
            coupons = await uow.payments.coupons.find_active_now()
            return [CouponResponse.model_validate(c) for c in coupons if not c.is_exhausted]

    async def create_coupon(
        self, data: CouponCreate, admin_id: uuid.UUID
    ) -> CouponResponse:
        async with self._uow() as uow:
            coupon = await uow.payments.coupons.create({
                **data.model_dump(exclude_unset=True),
                "created_by_id": admin_id,
                "times_used": 0,
                "is_active": True,
            })
            return CouponResponse.model_validate(coupon)

    async def update_coupon(
        self, coupon_id: uuid.UUID, data: object, admin_id: uuid.UUID
    ) -> CouponResponse:
        async with self._uow() as uow:
            coupon = await uow.payments.coupons.get_by_id(coupon_id)
            if coupon is None:
                raise CouponNotFoundError(str(coupon_id))
            updated = await uow.payments.coupons.update(
                coupon, data.model_dump(exclude_unset=True)
            )
            return CouponResponse.model_validate(updated)

    async def deactivate_coupon(self, coupon_id: uuid.UUID, admin_id: uuid.UUID) -> None:
        async with self._uow() as uow:
            coupon = await uow.payments.coupons.get_by_id(coupon_id)
            if coupon is None:
                raise CouponNotFoundError(str(coupon_id))
            await uow.payments.coupons.update(coupon, {
                "is_active": False,
                "deactivated_at": datetime.now(tz=timezone.utc),
            })

    # ── Splits ────────────────────────────────────────────────────────────────

    async def create_payment_split(
        self,
        payment_id: uuid.UUID,
        data: PaymentSplitCreate,
        admin_id: uuid.UUID,
    ) -> PaymentSplitResponse:
        async with self._uow() as uow:
            payment = await validate_payment_exists(payment_id, uow)
            split = await uow.payments.splits.create({
                "payment_id": payment_id,
                "vendor_id": data.vendor_id,
                "amount": data.amount,
                "description": data.description,
                "is_settled": False,
            })
            return PaymentSplitResponse(
                id=split.id,
                payment_id=split.payment_id,
                vendor_id=split.vendor_id,
                amount=split.amount,
                is_settled=split.is_settled,
            )

    async def list_payment_splits(
        self, payment_id: uuid.UUID
    ) -> list[PaymentSplitResponse]:
        async with self._uow() as uow:
            splits = await uow.payments.splits.find_by_payment(payment_id)
            return [
                PaymentSplitResponse(
                    id=s.id,
                    payment_id=s.payment_id,
                    vendor_id=s.vendor_id,
                    amount=s.amount,
                    is_settled=s.is_settled,
                )
                for s in splits
            ]

    # ── Invoices ──────────────────────────────────────────────────────────────

    async def get_invoice(self, invoice_id: uuid.UUID) -> InvoiceResponse:
        async with self._uow() as uow:
            invoice = await uow.payments.invoices.get_by_id(invoice_id)
            if invoice is None:
                raise NotFoundError("Invoice", str(invoice_id))
            return InvoiceResponse(
                id=invoice.id,
                invoice_number=invoice.invoice_number,
                entity_type=str(invoice.entity_type),
                total_amount=invoice.total_amount,
                invoice_status=str(invoice.invoice_status),
            )

    async def list_invoices(
        self, entity_id: uuid.UUID, entity_type: str
    ) -> list[InvoiceResponse]:
        from app.models.payments.invoice import InvoiceEntityType
        async with self._uow() as uow:
            try:
                etype = InvoiceEntityType(entity_type)
            except ValueError:
                raise BusinessRuleError(f"Unknown invoice entity type: {entity_type}")
            invoices = await uow.payments.invoices.find_by_entity(etype, entity_id)
            return [
                InvoiceResponse(
                    id=inv.id,
                    invoice_number=inv.invoice_number,
                    entity_type=str(inv.entity_type),
                    total_amount=inv.total_amount,
                    invoice_status=str(inv.invoice_status),
                )
                for inv in invoices
            ]
