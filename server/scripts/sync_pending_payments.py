"""
Settle open payments from Razorpay's own record of their orders.

For payments whose checkout succeeded on Razorpay but whose verify call and
webhook never reached the server, so they (and their bookings) were left
PENDING. For each open payment with a real Razorpay order it asks Razorpay
whether the order was paid; when it was, the capture is recorded and the
booking confirmed exactly as a successful verify would (including the
booking-confirmed notifications and emails).

Needs the production RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET and DATABASE_URL
in the environment (or server/.env).

Run from the server/ directory:
    python scripts/sync_pending_payments.py              # dry run: report only
    python scripts/sync_pending_payments.py --apply      # settle paid orders
    python scripts/sync_pending_payments.py --days 30    # look further back (default 14)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.payments.payment import Payment  # noqa: E402
from app.services.payments.service import (  # noqa: E402
    _GATEWAY_SYNCABLE_STATUSES,
    PaymentService,
    _razorpay_client,
)


async def main(apply: bool, days: int) -> None:
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(Payment.id, Payment.payment_number, Payment.payment_status, Payment.gateway_order_id)
            .where(
                Payment.payment_status.in_(list(_GATEWAY_SYNCABLE_STATUSES)),
                Payment.gateway_order_id.like("order_%"),
                Payment.created_at >= since,
            )
            .order_by(Payment.created_at)
        )
        candidates = rows.all()

    print(f"{len(candidates)} open payment(s) with a Razorpay order in the last {days} day(s).")
    client = _razorpay_client()
    service = PaymentService()
    settled = 0
    for payment_id, number, status, order_id in candidates:
        items = (await asyncio.to_thread(client.order.payments, order_id)).get("items", [])
        states = ", ".join(f"{p.get('id')}={p.get('status')}" for p in items) or "no payment attempts"
        paid = any(p.get("status") in ("captured", "authorized") for p in items)
        print(f"- {number} [{status.value}] {order_id}: {states}")
        if paid and apply:
            result = await service.sync_payment_with_gateway(payment_id)
            if result is not None:
                settled += 1
                print(f"    settled -> {result.payment_status.value}")
            else:
                print("    not settled (authorized amount did not match, or capture failed)")

    if apply:
        print(f"Done. Settled {settled} payment(s).")
    else:
        print("Dry run. Re-run with --apply to settle the paid ones.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="settle paid orders (default: dry run)")
    parser.add_argument("--days", type=int, default=14, help="how far back to look (default 14)")
    args = parser.parse_args()
    asyncio.run(main(apply=args.apply, days=args.days))
