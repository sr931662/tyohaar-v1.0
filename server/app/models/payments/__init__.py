"""
Payments domain — financial records for booking payments, settlements, and refunds.

Import order follows dependency graph (leaf models first):
  Coupon (no deps within payments)
  PaymentTransaction, PaymentSplit, Refund, PaymentAttempt
  → Payment (defines PaymentGateway enum used by PaymentWebhook)
  → PaymentWebhook
  → Invoice (references Payment)
  → Transaction (references Payment)

INTERNAL: PaymentSplit.vendor_id must NEVER be exposed to customers.
"""

from app.models.payments.coupon import Coupon
from app.models.payments.payment_transaction import PaymentTransaction
from app.models.payments.payment_split import PaymentSplit, SplitType
from app.models.payments.refund import Refund, RefundType, RefundReason
from app.models.payments.payment_attempt import PaymentAttempt, PaymentAttemptStatus
from app.models.payments.payment import Payment, PaymentGateway
from app.models.payments.payment_webhook import PaymentWebhook
from app.models.payments.invoice import Invoice, InvoiceEntityType
from app.models.payments.transaction import (
    Transaction,
    TransactionDirection,
    ReconciliationStatus,
    PartyType,
)

__all__ = [
    # Models
    "Coupon",
    "Payment",
    "PaymentTransaction",
    "PaymentSplit",
    "Refund",
    "PaymentAttempt",
    "PaymentWebhook",
    "Invoice",
    "Transaction",
    # Local enums (move to enums.py in next enums update)
    "PaymentGateway",
    "SplitType",
    "RefundType",
    "RefundReason",
    "PaymentAttemptStatus",
    "InvoiceEntityType",
    "TransactionDirection",
    "ReconciliationStatus",
    "PartyType",
]
