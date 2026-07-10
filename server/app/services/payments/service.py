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

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.enums import (
    CouponType,
    PaymentStatus,
    RefundStatus,
    TransactionType,
)
from app.models.payments.payment import PaymentGateway
from app.models.payments.payment_attempt import PaymentAttemptStatus
from app.models.payments.refund import RefundReason, RefundType
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
from app.services.exceptions import BusinessRuleError, ExternalServiceError, NotFoundError
from app.services.payments.exceptions import (
    CouponNotFoundError,
    InvalidGatewaySignatureError,
    PaymentAlreadyFailedError,
)
from app.services.payments.helpers import (
    apply_membership_discount,
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


@dataclass
class VendorEarningsPayment:
    """One payment row in a vendor's earnings/transaction history."""

    id: uuid.UUID
    payment_number: str
    booking_id: uuid.UUID
    amount: Decimal
    currency: str
    payment_status: str
    payment_method: str | None
    captured_at: datetime | None
    created_at: datetime


@dataclass
class VendorEarningsSummary:
    """
    Razorpay-payment-derived earnings analytics for a single vendor,
    scoped to that vendor's own bookings only (no platform-wide data).
    """

    total_collected: Decimal
    pending_amount: Decimal
    total_bookings_paid: int
    payments: list[VendorEarningsPayment]


def _generate_txn_number() -> str:
    import secrets
    suffix = str(secrets.randbelow(1_000_000)).zfill(6)
    year = datetime.now(tz=timezone.utc).year
    return f"TXN-{year}-{suffix}"


def _razorpay_client():
    """Return a configured Razorpay SDK client, or raise if credentials are unset."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ExternalServiceError(
            "razorpay",
            "Razorpay is not configured yet. Set RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET.",
        )
    import razorpay
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _rupees_to_paise(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


async def _notify_payment_outcome(
    payer_id: uuid.UUID,
    is_success: bool,
    payment_number: str,
    amount: Decimal,
) -> None:
    """
    Fire an in-app notification on payment success/failure. Since notifications
    are fetched from the server on every device signed into the same account,
    this is what makes "the plan shows up on all my devices" work — no
    device-specific push wiring needed for that guarantee.
    """
    from app.models.enums import NotificationChannel, NotificationType
    from app.schemas.notifications.create import NotificationCreate
    from app.services.notifications.service import NotificationService

    try:
        if is_success:
            data = NotificationCreate(
                user_id=payer_id,
                notification_type=NotificationType.PAYMENT_RECEIVED,
                channel=NotificationChannel.IN_APP,
                title="Payment received",
                body=f"Your payment of ₹{amount} for {payment_number} was successful. Your plan is now active.",
                reference_type="payment",
            )
        else:
            data = NotificationCreate(
                user_id=payer_id,
                notification_type=NotificationType.PAYMENT_FAILED,
                channel=NotificationChannel.IN_APP,
                title="Payment failed",
                body=f"Your payment of ₹{amount} for {payment_number} could not be completed. Please try again.",
                reference_type="payment",
            )
        await NotificationService().send_notification(user_id=payer_id, data=data)
    except Exception:
        logger.exception("Failed to send payment outcome notification for payer=%s", payer_id)


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
        3. Apply the customer's active membership discount, if any, and
           recompute final_amount server-side (never trust the client's
           final_amount — it's only used pre-membership for schema
           self-validation on PaymentCreate).
        4. Create Payment (PENDING) + PaymentAttempt + Transaction ledger entry.
        5. Create the real order with the gateway (after commit) and persist
           its gateway_order_id.
        """
        validate_payment_amount(data.subtotal)
        gateway_value = data.gateway.value if data.gateway and hasattr(data.gateway, "value") else (
            str(data.gateway) if data.gateway else "razorpay"
        )
        validate_gateway_supported(gateway_value)

        platform_fee = calculate_platform_fee(data.subtotal)
        gst = calculate_gst(platform_fee)
        tax_amount = data.tax_amount + gst
        payment_number = generate_payment_reference()

        payment_obj: object = None
        async with self._uow() as uow:
            # Validate booking exists and belongs to this customer
            booking = await uow.bookings.bookings.get_by_id(booking_id)
            if booking is None:
                raise NotFoundError("Booking", str(booking_id))
            if booking.customer_id != customer_id:
                raise BusinessRuleError("Booking does not belong to this customer.")

            discount_amount = data.discount_amount
            membership = await uow.memberships.memberships.get_active_for_user(customer_id)
            if membership is not None:
                plan = await uow.memberships.plans.get_by_id(membership.plan_id)
                if plan is not None and plan.discount_percentage > 0:
                    discount_amount += apply_membership_discount(data.subtotal, plan.discount_percentage)

            # Referral milestone discount — first usable grant whose min_plan_price
            # is met, consumed (decremented) on use, oldest grant first.
            usable_grants = await uow.referrals.milestone_grants.find_usable_for_user(customer_id)
            for grant in usable_grants:
                if data.subtotal >= grant.min_plan_price:
                    discount_amount += apply_membership_discount(data.subtotal, grant.discount_percentage)
                    await uow.referrals.milestone_grants.update(grant, {
                        "plans_remaining": grant.plans_remaining - 1,
                    })
                    break

            final_amount = data.subtotal - discount_amount + tax_amount + platform_fee

            payment = await uow.payments.payments.create({
                "booking_id": booking_id,
                "payer_id": customer_id,
                "currency": data.currency,
                "subtotal": data.subtotal,
                "discount_amount": discount_amount,
                "tax_amount": tax_amount,
                "platform_fee": platform_fee,
                "final_amount": final_amount,
                "payment_status": PaymentStatus.PENDING,
                "payment_method": data.payment_method,
                "gateway": data.gateway or PaymentGateway.RAZORPAY,
                "payment_number": payment_number,
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

        # Side effect (real gateway order creation) happens after commit so a
        # gateway outage never rolls back the Payment/ledger rows above.
        gateway_order_id = f"order_{payment_number.lower()}"
        if gateway_value == "razorpay":
            client = _razorpay_client()
            try:
                order = client.order.create({
                    "amount": _rupees_to_paise(payment_obj.final_amount),
                    "currency": payment_obj.currency.value if hasattr(payment_obj.currency, "value") else str(payment_obj.currency),
                    "receipt": payment_number,
                    "notes": {"payment_id": str(payment_obj.id), "booking_id": str(booking_id)},
                })
            except Exception as exc:
                logger.exception("Razorpay order creation failed for payment %s", payment_obj.id)
                raise ExternalServiceError("razorpay", "Could not create gateway order. Please try again.") from exc

            gateway_order_id = order["id"]
            async with self._uow() as uow:
                fresh = await uow.payments.payments.get_by_id(payment_obj.id)
                payment_obj = await uow.payments.payments.update(fresh, {"gateway_order_id": gateway_order_id})

        return PaymentInitResponse(
            payment_id=payment_obj.id,
            payment_number=payment_obj.payment_number,
            gateway_order_id=gateway_order_id,
            checkout_url=None,  # Razorpay Checkout is opened client-side with the order_id
            amount=payment_obj.final_amount,
            gateway=gateway_value,
        )

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
        2. Store the raw event first (STORE FIRST principle) — skip if this
           event_id was already delivered (gateway retries duplicates).
        3. Parse payload for gateway_order_id and success/failure status.
        4. Skip if payment already COMPLETED or FAILED (idempotency).
        5. On SUCCESS: complete payment, record transaction, write ledger,
           sync the booking's payment_status.
        6. On FAILURE: mark payment FAILED, increment attempt count.
        """
        if not verify_webhook_signature(payload, signature, secret, gateway):
            raise InvalidGatewaySignatureError()

        # Minimal payload parsing — expand per gateway SDK spec
        import json
        try:
            body = json.loads(payload)
        except Exception:
            raise ExternalServiceError(gateway, "Could not parse webhook payload.")

        event = body.get("event", "")
        event_id = body.get("id") or ""

        # Razorpay delivers refund events on the same webhook URL as payment
        # events — dispatch by event prefix rather than a separate endpoint.
        if event.startswith("refund."):
            await self._process_refund_webhook_event(gateway, event, event_id, body)
            return

        entity = body.get("payload", {}).get("payment", {}).get("entity", {})
        gateway_order_id = entity.get("order_id")
        gateway_payment_id = entity.get("id")
        is_success = event == "payment.captured"

        now = datetime.now(tz=timezone.utc)
        payment_outcome: tuple[uuid.UUID, bool, str, Decimal] | None = None
        referral_trigger: tuple[uuid.UUID, Decimal, uuid.UUID] | None = None

        async with self._uow() as uow:
            already_seen = False
            if event_id:
                existing_event = await uow.payments.webhooks.find_by_event_id(event_id, gateway=gateway)
                already_seen = existing_event is not None

            payment = None
            if not already_seen and gateway_order_id:
                payment = await uow.payments.payments.find_by_gateway_order(gateway_order_id)

            if already_seen:
                logger.info("Duplicate webhook event_id=%s for gateway=%s; skipping.", event_id, gateway)
            else:
                await uow.payments.webhooks.create({
                    "event_id": event_id or f"{gateway}_{now.timestamp()}",
                    "gateway": gateway,
                    "event_type": event,
                    "payment_id": payment.id if payment else None,
                    "is_signature_verified": True,
                    "raw_payload": body,
                    "is_processed": payment is not None,
                    "received_at": now,
                    "processed_at": now if payment is not None else None,
                })

                if payment is None:
                    logger.warning("Webhook for unknown gateway_order_id=%s", gateway_order_id)
                # Idempotency guard — a payment only transitions out of PENDING once
                elif payment.payment_status in (PaymentStatus.COMPLETED, PaymentStatus.FAILED):
                    pass
                elif is_success:
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

                    booking = await uow.bookings.bookings.get_by_id(payment.booking_id)
                    if booking is not None:
                        await uow.bookings.bookings.update(booking, {"payment_status": PaymentStatus.COMPLETED})

                    payment_outcome = (payment.payer_id, True, payment.payment_number, payment.final_amount)
                    referral_trigger = (payment.payer_id, payment.final_amount, payment.booking_id)
                else:
                    await uow.payments.payments.update(payment, {
                        "payment_status": PaymentStatus.FAILED,
                        "failed_at": now,
                    })

                    booking = await uow.bookings.bookings.get_by_id(payment.booking_id)
                    if booking is not None:
                        await uow.bookings.bookings.update(booking, {"payment_status": PaymentStatus.FAILED})

                    # Increment attempt counter
                    attempts = await uow.payments.attempts.find_by_payment(payment.id)
                    if attempts:
                        latest = attempts[-1]
                        await uow.payments.attempts.update(latest, {
                            "attempt_status": PaymentAttemptStatus.FAILED,
                            "completed_at": now,
                        })

                    payment_outcome = (payment.payer_id, False, payment.payment_number, payment.final_amount)

        if payment_outcome is not None:
            payer_id, was_success, pay_number, pay_amount = payment_outcome
            await _notify_payment_outcome(payer_id, was_success, pay_number, pay_amount)

        if referral_trigger is not None:
            referee_id, booking_amount, booking_id = referral_trigger
            try:
                from app.services.referrals.service import ReferralService
                await ReferralService().trigger_referral_rewards(
                    referee_id=referee_id, booking_amount=booking_amount, booking_id=booking_id
                )
            except Exception:
                logger.exception("Referral reward trigger failed for referee=%s booking=%s", referee_id, booking_id)

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
                "description": f"Payment captured via {gateway} (client verification)",
                "transacted_at": now,
            })

            booking = await uow.bookings.bookings.get_by_id(payment.booking_id)
            if booking is not None:
                await uow.bookings.bookings.update(booking, {"payment_status": PaymentStatus.COMPLETED})

            payer_id = payment.payer_id
            payment_number = payment.payment_number
            final_amount = payment.final_amount
            booking_id = payment.booking_id

            result = PaymentResponse.model_validate(payment)

        await _notify_payment_outcome(payer_id, True, payment_number, final_amount)

        try:
            from app.services.referrals.service import ReferralService
            await ReferralService().trigger_referral_rewards(
                referee_id=payer_id, booking_amount=final_amount, booking_id=booking_id
            )
        except Exception:
            logger.exception("Referral reward trigger failed for referee=%s booking=%s", payer_id, booking_id)

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
        customer_id: uuid.UUID | None,
        filters: PaymentFilters,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage[PaymentResponse]:
        async with self._uow() as uow:
            from app.models.payments.payment import Payment
            if customer_id is None:
                # Admin: return all payments
                payments = await uow.payments.payments.find_many(
                    order_by=Payment.created_at.desc(),
                    limit=limit,
                )
            else:
                payments = await uow.payments.payments.find_by_payer(
                    customer_id, skip=0, limit=limit
                )
            items = [PaymentResponse.model_validate(p) for p in payments]
            return CursorPage(items=items, has_more=len(items) == limit)

    async def get_vendor_earnings(self, vendor_id: uuid.UUID) -> VendorEarningsSummary:
        """
        Razorpay payment analytics scoped to one vendor's own bookings —
        replaces the old vendor payout wallet, which never had a live
        crediting path. Sourced directly from real Payment + Booking
        records via the same booking_id set list_vendor_bookings() uses.
        """
        from app.models.payments.payment import Payment

        async with self._uow() as uow:
            assignments = await uow.bookings.assignments.find_by_vendor(vendor_id, limit=10000)
            booking_ids = list({a.booking_id for a in assignments})
            if not booking_ids:
                return VendorEarningsSummary(
                    total_collected=Decimal("0.00"),
                    pending_amount=Decimal("0.00"),
                    total_bookings_paid=0,
                    payments=[],
                )

            payments = await uow.payments.payments.find_many(
                Payment.booking_id.in_(booking_ids),
                order_by=Payment.created_at.desc(),
                limit=200,
            )

            total_collected = sum(
                (p.final_amount for p in payments if p.payment_status == PaymentStatus.COMPLETED),
                Decimal("0.00"),
            )
            pending_amount = sum(
                (
                    p.final_amount
                    for p in payments
                    if p.payment_status in (PaymentStatus.PENDING, PaymentStatus.INITIATED, PaymentStatus.PROCESSING)
                ),
                Decimal("0.00"),
            )
            bookings_paid = len({
                p.booking_id for p in payments if p.payment_status == PaymentStatus.COMPLETED
            })

            return VendorEarningsSummary(
                total_collected=total_collected,
                pending_amount=pending_amount,
                total_bookings_paid=bookings_paid,
                payments=[
                    VendorEarningsPayment(
                        id=p.id,
                        payment_number=p.payment_number,
                        booking_id=p.booking_id,
                        amount=p.final_amount,
                        currency=p.currency.value if hasattr(p.currency, "value") else str(p.currency),
                        payment_status=p.payment_status.value if hasattr(p.payment_status, "value") else str(p.payment_status),
                        payment_method=(
                            p.payment_method.value if p.payment_method and hasattr(p.payment_method, "value") else p.payment_method
                        ),
                        captured_at=p.captured_at,
                        created_at=p.created_at,
                    )
                    for p in payments
                ],
            )

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
        Create a PENDING refund record and write the ledger entry, then call
        the gateway refund API after commit. A gateway failure here leaves
        the refund PENDING (visible to admins) rather than rolling back the
        DB record — the SDK call is retried by re-initiating the refund.
        """
        async with self._uow() as uow:
            payment = await validate_payment_exists(payment_id, uow)

            if payment.payment_status != PaymentStatus.COMPLETED:
                raise BusinessRuleError("Only COMPLETED payments can be refunded.")

            validate_refund_amount(payment, data.amount)

            now = datetime.now(tz=timezone.utc)
            # refund_reason is a fixed enum; free-text from the client goes into `notes` instead.
            valid_reason_values = {r.value for r in RefundReason}
            refund_reason = data.reason if data.reason in valid_reason_values else RefundReason.CUSTOMER_REQUEST
            refund = await uow.payments.refunds.create({
                "payment_id": payment_id,
                "booking_id": payment.booking_id,
                "refund_type": RefundType.FULL if data.amount == payment.final_amount else RefundType.PARTIAL,
                "refund_reason": refund_reason,
                "notes": data.reason,
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
            refund_id = refund.id
            gateway_payment_id = payment.gateway_payment_id
            gateway_val = payment.gateway.value if payment.gateway and hasattr(payment.gateway, "value") else str(payment.gateway)

        if gateway_val == "razorpay" and gateway_payment_id:
            try:
                client = _razorpay_client()
                gw_refund = client.payment.refund(gateway_payment_id, {
                    "amount": _rupees_to_paise(data.amount),
                    "speed": "normal",
                    "notes": {"reason": data.reason or "customer_request", "refund_id": str(refund_id)},
                })
            except Exception:
                logger.exception("Razorpay refund API call failed for refund %s", refund_id)
                # Refund stays PENDING; admin can retry — do not raise so the
                # already-committed refund record isn't hidden from the client.
            else:
                async with self._uow() as uow:
                    fresh = await uow.payments.refunds.get_by_id(refund_id)
                    updated = await uow.payments.refunds.update(fresh, {"gateway_refund_id": gw_refund.get("id")})
                    result = RefundResponse.model_validate(updated)

        return result

    async def _process_refund_webhook_event(
        self,
        gateway: str,
        event: str,
        event_id: str,
        body: dict,
    ) -> None:
        """Handle a refund.* event dispatched from handle_webhook (signature already verified)."""
        entity = body.get("payload", {}).get("refund", {}).get("entity", {})
        gateway_refund_id = entity.get("id")
        now = datetime.now(tz=timezone.utc)

        async with self._uow() as uow:
            if event_id:
                existing_event = await uow.payments.webhooks.find_by_event_id(event_id, gateway=gateway)
                if existing_event is not None:
                    logger.info("Duplicate refund webhook event_id=%s; skipping.", event_id)
                    return

            refund = None
            if gateway_refund_id:
                refund = await uow.payments.refunds.find_by_gateway_ref(gateway_refund_id)

            await uow.payments.webhooks.create({
                "event_id": event_id or f"{gateway}_{now.timestamp()}",
                "gateway": gateway,
                "event_type": event,
                "payment_id": refund.payment_id if refund else None,
                "is_signature_verified": True,
                "raw_payload": body,
                "is_processed": refund is not None,
                "received_at": now,
                "processed_at": now if refund is not None else None,
            })

            if refund is None:
                logger.warning("Refund webhook for unknown gateway_refund_id=%s", gateway_refund_id)
                return

            if event == "refund.processed" and refund.refund_status != RefundStatus.COMPLETED:
                await uow.payments.refunds.update(refund, {
                    "refund_status": RefundStatus.COMPLETED,
                    "processed_at": now,
                })
            elif event == "refund.failed" and refund.refund_status != RefundStatus.FAILED:
                await uow.payments.refunds.update(refund, {
                    "refund_status": RefundStatus.FAILED,
                    "failure_reason": entity.get("error_description") or "Gateway reported refund failure.",
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
