"""
Backfill script — recomputes subtotal/tax/total for bookings created with the
pre-`ccc91f1` pricing bug (flat platform_fee, subtotal ignoring
package.base_price), which produced rows like `subtotal=0, total_amount=1500`
for packages with no/free items. That bug is already fixed in
create_booking() for new bookings; this script corrects existing rows only.

Matches bookings WHERE subtotal = 0 AND total_amount > 0 — a pattern the
current create_booking() code cannot produce (platform_fee is hardcoded to
0.00, so subtotal=0 would force total_amount=0 too), making it a reliable
fingerprint of the old bug rather than a legitimate free booking.

Recomputes, for each match:
    subtotal      = package.base_price + sum(BookingItem.final_price)
    tax_amount    = round(subtotal * 0.18, 2)
    platform_fee  = 0.00
    total_amount  = subtotal + tax_amount
    amount_due    = total_amount - amount_paid

amount_paid is left untouched. Applied regardless of payment status — if a
booking already has a payment recorded, amount_due will reflect the corrected
total against whatever was actually paid; review the printed report for any
booking with amount_paid > 0 before applying.

Run from the server/ directory:
    python scripts/backfill_booking_totals.py            # dry run, prints report only
    python scripts/backfill_booking_totals.py --apply     # writes the changes
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Make sure `app` is importable when running from server/
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.config import settings  # noqa: loads .env
from app.db.session import AsyncSessionLocal
from app.models.bookings.booking import Booking
from app.models.bookings.booking_item import BookingItem
from app.models.packages.package import Package

TAX_RATE = Decimal("0.18")


async def find_affected_bookings(session) -> list[Booking]:
    result = await session.execute(
        select(Booking).where(Booking.subtotal == Decimal("0.00"), Booking.total_amount > Decimal("0.00"))
    )
    return list(result.scalars().all())


async def recompute(session, booking: Booking) -> dict | None:
    package = await session.get(Package, booking.package_id)
    package_base_price = package.base_price if package else Decimal("0.00")

    items_result = await session.execute(
        select(BookingItem).where(BookingItem.booking_id == booking.id)
    )
    items = list(items_result.scalars().all())
    items_total = sum((i.final_price for i in items), Decimal("0.00"))

    new_subtotal = (package_base_price or Decimal("0.00")) + items_total
    new_tax = (new_subtotal * TAX_RATE).quantize(Decimal("0.01"))
    new_total = new_subtotal + new_tax
    new_amount_due = new_total - booking.amount_paid

    return {
        "booking_number": booking.booking_number,
        "id": booking.id,
        "amount_paid": booking.amount_paid,
        "old": {
            "subtotal": booking.subtotal,
            "tax_amount": booking.tax_amount,
            "total_amount": booking.total_amount,
            "amount_due": booking.amount_due,
        },
        "new": {
            "subtotal": new_subtotal,
            "tax_amount": new_tax,
            "total_amount": new_total,
            "amount_due": new_amount_due,
        },
    }


def print_report(changes: list[dict]) -> None:
    if not changes:
        print("No bookings matched the buggy fingerprint (subtotal=0, total_amount>0). Nothing to do.")
        return

    print(f"\n{len(changes)} booking(s) matched:\n")
    for c in changes:
        flag = "  [PAID]" if c["amount_paid"] > 0 else ""
        print(f"  {c['booking_number']}  (id={c['id']}){flag}")
        print(f"    subtotal      {c['old']['subtotal']:>10} -> {c['new']['subtotal']:>10}")
        print(f"    tax_amount    {c['old']['tax_amount']:>10} -> {c['new']['tax_amount']:>10}")
        print(f"    total_amount  {c['old']['total_amount']:>10} -> {c['new']['total_amount']:>10}")
        print(f"    amount_due    {c['old']['amount_due']:>10} -> {c['new']['amount_due']:>10}")
        print()


async def main(apply: bool) -> None:
    print("\n=== Tyohaar -- Booking Totals Backfill ===")
    print(f"  Mode: {'APPLY (writing changes)' if apply else 'DRY RUN (no changes will be written)'}")

    async with AsyncSessionLocal() as session:
        bookings = await find_affected_bookings(session)
        changes = [c for c in (await asyncio.gather(*(recompute(session, b) for b in bookings))) if c]
        print_report(changes)

        if apply and changes:
            by_id = {b.id: b for b in bookings}
            for c in changes:
                booking = by_id[c["id"]]
                booking.subtotal = c["new"]["subtotal"]
                booking.tax_amount = c["new"]["tax_amount"]
                booking.platform_fee = Decimal("0.00")
                booking.total_amount = c["new"]["total_amount"]
                booking.amount_due = c["new"]["amount_due"]
            await session.commit()
            print(f"Applied. {len(changes)} booking(s) updated.\n")
        elif changes:
            print("Dry run only — re-run with --apply to write these changes.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = parser.parse_args()
    asyncio.run(main(args.apply))
