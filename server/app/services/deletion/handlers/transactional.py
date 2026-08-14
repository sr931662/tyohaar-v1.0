"""
Tier: field-level sanitisation of retained transactional records.

Retaining a booking must not mean retaining the event. Retaining an invoice
must not mean retaining the customer's profile. These rows survive because
they are financial records; the personal detail attached to them mostly does
not have that justification and is cleared here.

The module draws a hard line between two kinds of field:

  * **Clearly unnecessary** — a delivery recipient's phone, a host's free-text
    instructions, a raw gateway response blob. Nothing about the accounting
    purpose needs them. Cleared now.

  * **Possibly required** — the billing name, address and tax identifiers
    printed on a retained invoice. Whether these may be removed is a legal
    question, so they are left exactly as they are and reported as deferred.
    `app/core/retention.py` holds the two sets; moving a field from
    PENDING to SCRUBBABLE there is the only change needed once counsel rules.

Nothing in this module makes an irreversible decision about a field whose
necessity is unresolved, and no privacy claim may be published about any
field that appears in the deferred list.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.retention import (
    INVOICE_PENDING_COUNSEL_FIELDS,
    INVOICE_SCRUBBABLE_FIELDS,
    INVOICE_SNAPSHOT_PENDING_COUNSEL_KEYS,
    INVOICE_SNAPSHOT_SCRUBBABLE_KEYS,
    PURGE_INVOICE_PDFS,
)
from app.models.bookings.booking import Booking
from app.models.bookings.booking_invoice import BookingInvoice
from app.models.payments.invoice import Invoice
from app.models.payments.payment import Payment
from app.models.payments.payment_transaction import PaymentTransaction
from app.models.payments.refund import Refund
from app.models.payments.transaction import Transaction
from app.services.deletion.registry import (
    TIER_SANITISE,
    PurgeReport,
    register_purge,
)

#: Keys worth keeping out of a retained gateway response. Everything else in
#: the blob is dropped — we keep a curated subset rather than trying to
#: blocklist personal fields, because a gateway can add a field at any time
#: and an allowlist fails safe where a blocklist fails open.
_GATEWAY_KEEP_KEYS = frozenset(
    {
        "id",
        "order_id",
        "payment_id",
        "refund_id",
        "status",
        "amount",
        "currency",
        "method",
        "captured",
        "created_at",
        "error_code",
        "error_reason",
    }
)


@register_purge("booking_details", order=TIER_SANITISE + 40)
async def purge_booking_details(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Strip personal detail from retained bookings.

    `recipient_phone` is the highest-risk survivor anywhere in the retained
    set: a plain mobile number sitting in a table we keep for years. It has no
    accounting role once the service has been delivered.
    """
    report = PurgeReport(handler="booking_details")

    result = await session.execute(
        update(Booking)
        .where(Booking.customer_id == user_id)
        .values(
            recipient_name=None,
            recipient_phone=None,
            special_instructions=None,
            customization_note=None,
            cancellation_reason=None,
            # The address row itself is deleted; this FK is SET NULL anyway,
            # but clearing it explicitly keeps the intent visible.
            address_id=None,
        )
    )
    report.count("bookings_sanitised", result.rowcount or 0)

    return report


@register_purge("payment_details", order=TIER_SANITISE + 50)
async def purge_payment_details(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Reduce retained payment records to their accounting content.

    `payment_transactions.raw_response` is the quiet one: a full gateway JSON
    blob that routinely carries the customer's name, email and phone, kept for
    the entire financial retention window with no accounting need for anything
    beyond the amount, status and reference.
    """
    report = PurgeReport(handler="payment_details")

    # Gateway blobs, reached through the user's payments.
    rows = (
        (
            await session.execute(
                select(PaymentTransaction.id, PaymentTransaction.raw_response)
                .join(Payment, PaymentTransaction.payment_id == Payment.id)
                .where(Payment.payer_id == user_id)
            )
        )
        .tuples()
        .all()
    )

    reduced = 0
    for tx_id, raw in rows:
        if not raw:
            continue
        kept = {k: v for k, v in raw.items() if k in _GATEWAY_KEEP_KEYS}
        if kept != raw:
            await session.execute(
                update(PaymentTransaction)
                .where(PaymentTransaction.id == tx_id)
                .values(raw_response=kept or None, error_message=None)
            )
            reduced += 1
    report.count("gateway_responses_reduced", reduced)

    # Free text on refunds and ledger transactions. Structured status codes
    # and reference numbers are the accounting record; prose is not.
    result = await session.execute(
        update(Refund)
        .where(Refund.initiated_by_id == user_id)
        .values(notes=None, failure_reason=None)
    )
    report.count("refunds_sanitised", result.rowcount or 0)

    result = await session.execute(
        update(Transaction)
        .where(Transaction.payer_id == user_id)
        .values(description=None, reconciliation_notes=None, context_data=None)
    )
    report.count("transactions_sanitised", result.rowcount or 0)

    return report


@register_purge("invoice_details", order=TIER_SANITISE + 60)
async def purge_invoice_details(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Clear only the invoice fields counsel has confirmed are unnecessary.

    Ships doing almost nothing on purpose. `INVOICE_SCRUBBABLE_FIELDS` is
    empty until counsel rules, so every billing field is currently reported as
    deferred and left untouched. The machinery is here and tested; enabling it
    is a one-line change in `app/core/retention.py`, not a redesign.
    """
    report = PurgeReport(handler="invoice_details")

    # ── Discrete columns on booking_invoices ──────────────────────────────────
    if INVOICE_SCRUBBABLE_FIELDS:
        columns = {
            name: None
            for name in INVOICE_SCRUBBABLE_FIELDS
            if hasattr(BookingInvoice, name)
        }
        if columns:
            result = await session.execute(
                update(BookingInvoice)
                .where(
                    BookingInvoice.booking_id.in_(
                        select(Booking.id).where(Booking.customer_id == user_id)
                    )
                )
                .values(**columns)
            )
            report.count("booking_invoices_scrubbed", result.rowcount or 0)

    if INVOICE_PENDING_COUNSEL_FIELDS:
        report.defer(
            "invoice billing fields retained pending counsel: "
            + ", ".join(sorted(INVOICE_PENDING_COUNSEL_FIELDS))
        )

    # ── billing_snapshot JSONB on invoices ────────────────────────────────────
    if INVOICE_SNAPSHOT_SCRUBBABLE_KEYS:
        rows = (
            (
                await session.execute(
                    select(Invoice.id, Invoice.billing_snapshot).where(
                        Invoice.customer_id == user_id
                    )
                )
            )
            .tuples()
            .all()
        )
        scrubbed = 0
        for invoice_id, snapshot in rows:
            if not snapshot:
                continue
            kept = {
                k: v
                for k, v in snapshot.items()
                if k not in INVOICE_SNAPSHOT_SCRUBBABLE_KEYS
            }
            if kept != snapshot:
                await session.execute(
                    update(Invoice)
                    .where(Invoice.id == invoice_id)
                    .values(billing_snapshot=kept or None)
                )
                scrubbed += 1
        report.count("billing_snapshots_scrubbed", scrubbed)

    if INVOICE_SNAPSHOT_PENDING_COUNSEL_KEYS:
        report.defer(
            "invoices.billing_snapshot keys retained pending counsel: "
            + ", ".join(sorted(INVOICE_SNAPSHOT_PENDING_COUNSEL_KEYS))
        )

    # Free text with no statutory role goes regardless of the above.
    result = await session.execute(
        update(Invoice)
        .where(Invoice.customer_id == user_id)
        .values(cancellation_reason=None)
    )
    report.count("invoice_free_text_cleared", result.rowcount or 0)

    # ── Generated PDFs ────────────────────────────────────────────────────────
    # A stored PDF renders the same billing details as the row, so leaving it
    # in place makes any field-level sanitisation cosmetic. Deleting it changes
    # how historical invoices are served, which is a client decision.
    if not PURGE_INVOICE_PDFS:
        pdf_count = len(
            (
                await session.execute(
                    select(Invoice.id).where(
                        Invoice.customer_id == user_id,
                        Invoice.invoice_url.isnot(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        if pdf_count:
            report.count("invoice_pdfs_retained", pdf_count)
            report.defer(
                f"{pdf_count} invoice PDF(s) retained at their CDN URLs — "
                "PURGE_INVOICE_PDFS is off pending client decision"
            )

    return report
