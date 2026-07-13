"""
Payment repository — Payment and all payment-domain child models.

Sub-repositories:
  payments          — Payment (gateway-level payment record)
  transactions      — PaymentTransaction (gateway API interaction logs)
  attempts          — PaymentAttempt (each payment attempt)
  splits            — PaymentSplit (vendor payout splits)
  refunds           — Refund
  webhooks          — PaymentWebhook
  coupons           — Coupon (discount codes)
  invoices          — Invoice (non-booking formal invoices)
  ledger            — Transaction (platform financial ledger — IMMUTABLE)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    CouponApplicability,
    CouponType,
    Currency,
    InvoiceStatus,
    PaymentStatus,
    SettlementStatus,
    TransactionType,
)
from app.models.payments.coupon import Coupon
from app.models.payments.coupon_redemption import CouponRedemption
from app.models.payments.invoice import Invoice, InvoiceEntityType
from app.models.payments.payment import Payment
from app.models.payments.payment_attempt import PaymentAttempt
from app.models.payments.payment_split import PaymentSplit
from app.models.payments.payment_transaction import PaymentTransaction
from app.models.payments.payment_webhook import PaymentWebhook
from app.models.payments.refund import Refund
from app.models.payments.transaction import Transaction, ReconciliationStatus, TransactionDirection
from app.repositories.base import BaseRepository, RepositoryError


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Payment)

    async def find_by_number(self, payment_number: str) -> Payment | None:
        return await self.find_one(Payment.payment_number == payment_number)

    async def find_by_booking(self, booking_id: uuid.UUID) -> list[Payment]:
        return await self.find_many(
            Payment.booking_id == booking_id,
            order_by=Payment.created_at.desc(),
        )

    async def find_by_payer(
        self,
        payer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Payment]:
        return await self.find_many(
            Payment.payer_id == payer_id,
            order_by=Payment.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_status(
        self,
        status: PaymentStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        return await self.find_many(
            Payment.payment_status == status,
            skip=skip,
            limit=limit,
        )

    async def find_by_gateway_order(self, gateway_order_id: str) -> Payment | None:
        return await self.find_one(Payment.gateway_order_id == gateway_order_id)

    async def find_by_gateway_payment(self, gateway_payment_id: str) -> Payment | None:
        return await self.find_one(Payment.gateway_payment_id == gateway_payment_id)

    async def find_pending(self, *, skip: int = 0, limit: int = 100) -> list[Payment]:
        return await self.find_many(
            Payment.payment_status == PaymentStatus.PENDING,
            skip=skip,
            limit=limit,
        )

    async def find_completed(
        self,
        payer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Payment]:
        return await self.find_many(
            Payment.payer_id == payer_id,
            Payment.payment_status == PaymentStatus.COMPLETED,
            order_by=Payment.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def get_with_transactions(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.get_by_id(
            payment_id,
            options=[selectinload(Payment.transactions)],
        )

    async def get_with_refunds(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.get_by_id(
            payment_id,
            options=[selectinload(Payment.refunds)],
        )

    async def count_by_status(self) -> dict[str, int]:
        stmt = (
            select(Payment.payment_status, func.count().label("count"))
            .group_by(Payment.payment_status)
        )
        result = await self._session.execute(stmt)
        return {str(row.payment_status): row.count for row in result.all()}


class PaymentTransactionRepository(BaseRepository[PaymentTransaction]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaymentTransaction)

    async def find_by_payment(self, payment_id: uuid.UUID) -> list[PaymentTransaction]:
        return await self.find_many(
            PaymentTransaction.payment_id == payment_id,
            order_by=PaymentTransaction.created_at.asc(),
        )

    async def find_by_gateway_ref(self, gateway_ref: str) -> PaymentTransaction | None:
        return await self.find_one(PaymentTransaction.gateway_transaction_id == gateway_ref)


class PaymentAttemptRepository(BaseRepository[PaymentAttempt]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaymentAttempt)

    async def find_by_payment(self, payment_id: uuid.UUID) -> list[PaymentAttempt]:
        return await self.find_many(
            PaymentAttempt.payment_id == payment_id,
            order_by=PaymentAttempt.created_at.asc(),
        )

    async def count_for_payment(self, payment_id: uuid.UUID) -> int:
        return await self.count(PaymentAttempt.payment_id == payment_id)


class PaymentSplitRepository(BaseRepository[PaymentSplit]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaymentSplit)

    async def find_by_payment(self, payment_id: uuid.UUID) -> list[PaymentSplit]:
        return await self.find_many(PaymentSplit.payment_id == payment_id)

    async def find_pending_settlement(self) -> list[PaymentSplit]:
        return await self.find_many(PaymentSplit.is_settled == False)  # noqa: E712


class RefundRepository(BaseRepository[Refund]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Refund)

    async def find_by_payment(self, payment_id: uuid.UUID) -> list[Refund]:
        return await self.find_many(
            Refund.payment_id == payment_id,
            order_by=Refund.created_at.desc(),
        )

    async def find_by_booking(self, booking_id: uuid.UUID) -> list[Refund]:
        return await self.find_many(Refund.booking_id == booking_id)

    async def find_pending(self) -> list[Refund]:
        return await self.find_many(Refund.refund_status == "pending")

    async def find_by_gateway_ref(self, gateway_ref: str) -> Refund | None:
        return await self.find_one(Refund.gateway_refund_id == gateway_ref)


class PaymentWebhookRepository(BaseRepository[PaymentWebhook]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaymentWebhook)

    async def find_by_event_id(self, event_id: str, gateway: str | None = None) -> PaymentWebhook | None:
        if gateway is not None:
            return await self.find_one(
                PaymentWebhook.event_id == event_id,
                PaymentWebhook.gateway == gateway,
            )
        return await self.find_one(PaymentWebhook.event_id == event_id)

    async def find_unprocessed(self) -> list[PaymentWebhook]:
        return await self.find_many(PaymentWebhook.is_processed == False)  # noqa: E712

    async def find_failed(self) -> list[PaymentWebhook]:
        return await self.find_many(PaymentWebhook.processing_error.is_not(None))


class CouponRepository(BaseRepository[Coupon]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Coupon)

    async def find_by_code(self, code: str) -> Coupon | None:
        """Code is stored uppercase; caller should normalize before lookup."""
        return await self.find_one(Coupon.code == code.upper())

    async def find_active_now(self) -> list[Coupon]:
        """Return all currently redeemable coupons."""
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            Coupon.is_active == True,  # noqa: E712
            Coupon.valid_from <= now,
            (Coupon.valid_until.is_(None)) | (Coupon.valid_until >= now),
            order_by=Coupon.valid_until.asc(),
        )

    async def find_by_type(
        self,
        coupon_type: CouponType,
        *,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Coupon]:
        filters = [Coupon.coupon_type == coupon_type]
        if active_only:
            filters.append(Coupon.is_active == True)  # noqa: E712
        return await self.find_many(*filters, skip=skip, limit=limit)

    async def find_by_applicability(
        self,
        applicability: CouponApplicability,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Coupon]:
        return await self.find_many(
            Coupon.applicability == applicability,
            Coupon.is_active == True,  # noqa: E712
            skip=skip,
            limit=limit,
        )

    async def find_system_generated(self) -> list[Coupon]:
        return await self.find_many(
            Coupon.is_system_generated == True,  # noqa: E712
            order_by=Coupon.created_at.desc(),
        )

    async def find_expiring_soon(
        self,
        before: datetime,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Coupon]:
        return await self.find_many(
            Coupon.is_active == True,  # noqa: E712
            Coupon.valid_until.is_not(None),
            Coupon.valid_until <= before,
            order_by=Coupon.valid_until.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_exhausted(self) -> list[Coupon]:
        """Coupons that have reached their total_usage_limit."""
        stmt = (
            select(Coupon)
            .where(Coupon.total_usage_limit.is_not(None))
            .where(Coupon.times_used >= Coupon.total_usage_limit)
            .where(Coupon.is_active == True)  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_lock(self, coupon_id: uuid.UUID) -> Coupon | None:
        """SELECT FOR UPDATE — used by checkout to atomically check + increment usage."""
        stmt = (
            select(Coupon)
            .where(Coupon.id == coupon_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_usage(self, coupon_id: uuid.UUID) -> None:
        stmt = (
            update(Coupon)
            .where(Coupon.id == coupon_id)
            .values(times_used=Coupon.times_used + 1)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def find_first_booking_coupons(self) -> list[Coupon]:
        return await self.find_many(
            Coupon.first_booking_only == True,  # noqa: E712
            Coupon.is_active == True,  # noqa: E712
        )


class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Invoice)

    async def find_by_number(self, invoice_number: str) -> Invoice | None:
        return await self.find_one(Invoice.invoice_number == invoice_number)

    async def find_by_entity(
        self,
        entity_type: InvoiceEntityType,
        entity_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Invoice]:
        return await self.find_many(
            Invoice.entity_type == entity_type,
            Invoice.entity_id == entity_id,
            order_by=Invoice.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_customer(
        self,
        customer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Invoice]:
        return await self.find_many(
            Invoice.customer_id == customer_id,
            order_by=Invoice.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_payment(self, payment_id: uuid.UUID) -> list[Invoice]:
        return await self.find_many(
            Invoice.payment_id == payment_id,
            order_by=Invoice.created_at.desc(),
        )

    async def find_by_status(
        self,
        status: InvoiceStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Invoice]:
        return await self.find_many(
            Invoice.invoice_status == status,
            order_by=Invoice.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_unpaid(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Invoice]:
        return await self.find_many(
            Invoice.invoice_status.in_([
                InvoiceStatus.DRAFT,
                InvoiceStatus.SENT,
                InvoiceStatus.OVERDUE,
            ]),
            order_by=Invoice.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_overdue(self) -> list[Invoice]:
        return await self.find_many(
            Invoice.invoice_status == InvoiceStatus.OVERDUE,
            order_by=Invoice.created_at.asc(),
        )

    async def find_by_type(
        self,
        entity_type: InvoiceEntityType,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Invoice]:
        return await self.find_many(
            Invoice.entity_type == entity_type,
            order_by=Invoice.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_credit_notes(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Invoice]:
        return await self.find_many(
            Invoice.is_credit_note == True,  # noqa: E712
            order_by=Invoice.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_membership_invoices_for_customer(
        self,
        customer_id: uuid.UUID,
    ) -> list[Invoice]:
        return await self.find_many(
            Invoice.customer_id == customer_id,
            Invoice.entity_type == InvoiceEntityType.MEMBERSHIP,
            order_by=Invoice.created_at.desc(),
        )


class PlatformTransactionRepository(BaseRepository[Transaction]):
    """
    IMMUTABLE: only create() is permitted.
    The transactions table is the platform's financial ledger — no row may
    ever be updated or deleted. Corrections are reversal transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Transaction)

    async def update(self, instance: Transaction, data: dict) -> Transaction:  # type: ignore[override]
        raise RepositoryError("Transaction ledger is immutable — updates are not permitted.")

    async def delete(self, instance: Transaction) -> None:  # type: ignore[override]
        raise RepositoryError("Transaction ledger is immutable — deletes are not permitted.")

    async def soft_delete(self, instance: Transaction) -> None:  # type: ignore[override]
        raise RepositoryError("Transaction ledger is immutable — soft deletes are not permitted.")

    async def bulk_update(self, ids: list[uuid.UUID], data: dict) -> int:  # type: ignore[override]
        raise RepositoryError("Transaction ledger is immutable — bulk updates are not permitted.")

    async def bulk_delete(self, ids: list[uuid.UUID]) -> int:  # type: ignore[override]
        raise RepositoryError("Transaction ledger is immutable — bulk deletes are not permitted.")

    # ── Queries ───────────────────────────────────────────────────────────────

    async def find_by_number(self, transaction_number: str) -> Transaction | None:
        return await self.find_one(Transaction.transaction_number == transaction_number)

    async def find_by_payment(
        self,
        payment_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.payment_id == payment_id,
            order_by=Transaction.transacted_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_booking(
        self,
        booking_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.booking_id == booking_id,
            order_by=Transaction.transacted_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_payer(
        self,
        payer_type: str,
        payer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.payer_type == payer_type,
            Transaction.payer_id == payer_id,
            order_by=Transaction.transacted_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_payee(
        self,
        payee_type: str,
        payee_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.payee_type == payee_type,
            Transaction.payee_id == payee_id,
            order_by=Transaction.transacted_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_type(
        self,
        transaction_type: TransactionType,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.transaction_type == transaction_type,
            order_by=Transaction.transacted_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_direction(
        self,
        direction: TransactionDirection,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.direction == direction,
            order_by=Transaction.transacted_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_pending_settlement(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.settlement_status == SettlementStatus.PENDING,
            order_by=Transaction.transacted_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_settlement_batch(
        self,
        batch_id: uuid.UUID,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.settlement_batch_id == batch_id,
            order_by=Transaction.transacted_at.asc(),
        )

    async def find_by_reconciliation_status(
        self,
        status: ReconciliationStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.reconciliation_status == status,
            order_by=Transaction.transacted_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_in_range(
        self,
        start: datetime,
        end: datetime,
        *,
        skip: int = 0,
        limit: int = 500,
    ) -> list[Transaction]:
        return await self.find_many(
            Transaction.transacted_at >= start,
            Transaction.transacted_at <= end,
            order_by=Transaction.transacted_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_reversals(self) -> list[Transaction]:
        return await self.find_many(
            Transaction.is_reversal == True,  # noqa: E712
            order_by=Transaction.transacted_at.desc(),
        )

    async def find_reversals_for(self, original_id: uuid.UUID) -> list[Transaction]:
        return await self.find_many(
            Transaction.reversal_of_id == original_id,
            order_by=Transaction.transacted_at.asc(),
        )

    async def find_by_gateway_ref(self, gateway_reference: str) -> Transaction | None:
        return await self.find_one(Transaction.gateway_reference == gateway_reference)


class CouponRedemptionRepository(BaseRepository[CouponRedemption]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CouponRedemption)

    async def count_for_user(self, coupon_id: uuid.UUID, user_id: uuid.UUID) -> int:
        return await self.count(
            CouponRedemption.coupon_id == coupon_id,
            CouponRedemption.user_id == user_id,
        )


class PaymentRepositoryAggregate:
    """Groups all payment-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.payments = PaymentRepository(session)
        self.transactions = PaymentTransactionRepository(session)
        self.attempts = PaymentAttemptRepository(session)
        self.splits = PaymentSplitRepository(session)
        self.refunds = RefundRepository(session)
        self.webhooks = PaymentWebhookRepository(session)
        self.coupons = CouponRepository(session)
        self.coupon_redemptions = CouponRedemptionRepository(session)
        self.invoices = InvoiceRepository(session)
        self.ledger = PlatformTransactionRepository(session)
