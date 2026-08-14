"""
End-to-end verification of the account deletion pipeline against a real
Postgres, using one realistic user carrying the full data graph.

Run against a DISPOSABLE database only:

    TEST_DATABASE_URL=postgresql+asyncpg://.../tyohaar_scratch \
        python -m scripts.verify_deletion

The same three guards as the integration tests apply, and the strongest is the
first: the target may never be the database configured in server/.env.

What this proves that unit tests cannot: the RESTRICT foreign keys behave as
the tombstone design assumes, a booked celebration is sanitised rather than
deleted, guest PII runs on its own clock, and the pipeline reports INCOMPLETE
rather than success when an external object cannot be removed.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.models.base import Base  # noqa: E402
from app.models import *  # noqa: E402,F401,F403

from app.models.bookings.booking import Booking  # noqa: E402
from app.models.enums import (  # noqa: E402
    AccountStatus,
    BookingStatus,
    BookingType,
    DeletionRequestStatus,
    MediaUsage,
    PaymentStatus,
    TicketCategory,
    TransactionType,
    UserRole,
    UserType,
)
from app.models.invitations.invitation import Invitation  # noqa: E402
from app.models.invitations.invitation_guest import InvitationGuest  # noqa: E402
from app.models.media.image import Image  # noqa: E402
from app.models.media.video import Video  # noqa: E402
from app.models.occasions.celebration import Celebration  # noqa: E402
from app.models.occasions.celebration_guest import CelebrationGuest  # noqa: E402
from app.models.occasions.occasion import Occasion  # noqa: E402
from app.models.packages.package import Package  # noqa: E402
from app.models.packages.package_review import PackageReview  # noqa: E402
from app.models.payments.payment import Payment  # noqa: E402
from app.models.payments.transaction import (  # noqa: E402
    PartyType,
    Transaction,
    TransactionDirection,
)
from app.models.support.message import (  # noqa: E402
    SupportMessage,
    SupportSenderRole,
)
from app.models.support.ticket import SupportTicket  # noqa: E402
from app.models.users.address import UserAddress  # noqa: E402
from app.models.users.deletion_request import DeletionRequest  # noqa: E402
from app.models.users.device import UserDevice  # noqa: E402
from app.models.users.profile import UserProfile  # noqa: E402
from app.models.users.user import User  # noqa: E402
from app.services.deletion.service import DeletionService  # noqa: E402

URL = os.environ.get("TEST_DATABASE_URL")

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  - ' + detail) if detail else ''}")


# -- Guards --------------------------------------------------------------------


def assert_disposable(url: str) -> None:
    env = Path(__file__).resolve().parents[1] / ".env"
    configured = None
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                q = urlparse(raw.replace("postgresql+asyncpg://", "postgresql://"))
                configured = (
                    (q.hostname or "").lower(),
                    (q.path or "").lstrip("/").split("?")[0].lower(),
                )

    p = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
    target = ((p.hostname or "").lower(), (p.path or "").lstrip("/").split("?")[0].lower())

    if configured and target == configured:
        sys.exit(
            f"REFUSING: {target[1]!r} is the database configured in server/.env. "
            "This script destroys data. Use a scratch database."
        )
    if not any(m in target[1] for m in ("test", "staging", "scratch")):
        sys.exit(
            f"REFUSING: database {target[1]!r} is not named as disposable "
            "(needs 'test', 'staging' or 'scratch')."
        )
    print(f"guard OK - operating on {target[1]!r}\n")


# -- Fixture: one realistic user with the full graph ---------------------------


async def build_user(sf) -> dict:
    """Create a user carrying every category the matrix classifies."""
    ids: dict = {}
    async with sf() as s:
        occasion = Occasion(id=uuid.uuid4(), name="Anniversary", slug=f"anniv-{uuid.uuid4().hex[:8]}")
        package = Package(id=uuid.uuid4(), name="Gold Anniversary", slug=f"gold-{uuid.uuid4().hex[:8]}")
        s.add_all([occasion, package])

        user = User(
            id=uuid.uuid4(),
            phone="+919812345678",
            email="asha.verma@example.com",
            full_name="Asha Verma",
            first_name="Asha",
            last_name="Verma",
            role=UserRole.CUSTOMER,
            user_type=UserType.INDIVIDUAL,
            account_status=AccountStatus.ACTIVE,
        )
        s.add(user)
        s.add(UserProfile(id=uuid.uuid4(), user_id=user.id, city="Jaipur", bio="Loves marigolds"))
        s.add(UserAddress(
            id=uuid.uuid4(), user_id=user.id, recipient_name="Asha Verma",
            recipient_phone="+919812345678", address_line_1="21 Amber Road",
            city="Jaipur", state="Rajasthan", postal_code="302002",
        ))
        s.add(UserDevice(
            id=uuid.uuid4(), user_id=user.id, device_id="dev-abc",
            push_notification_token="fcm-token-xyz",
        ))

        # Two celebrations: one booked (must survive, sanitised), one not.
        booked = Celebration(
            id=uuid.uuid4(), customer_id=user.id, occasion_id=occasion.id,
            title="25th Anniversary", description="Silver jubilee at home",
            celebration_date=date.today() - timedelta(days=700),
            venue_name="Rambagh Lawn", venue_address="21 Amber Road, Jaipur",
            latitude=26.9124, longitude=75.7873,
            special_instructions="Ring the bell twice",
        )
        unbooked = Celebration(
            id=uuid.uuid4(), customer_id=user.id, occasion_id=occasion.id,
            title="Housewarming", celebration_date=date.today() + timedelta(days=40),
            venue_name="New Flat",
        )
        s.add_all([booked, unbooked])

        # Guests on both - the booked one's guests are the interesting case.
        s.add(CelebrationGuest(id=uuid.uuid4(), celebration_id=booked.id, name="Ravi Kapoor",
                               phone="+919900112233", email="ravi@example.com"))
        s.add(CelebrationGuest(id=uuid.uuid4(), celebration_id=unbooked.id, name="Meera Shah",
                               phone="+919900445566"))

        invitation = Invitation(
            id=uuid.uuid4(), invitation_number=f"INV-{uuid.uuid4().hex[:8]}",
            celebration_id=booked.id, owner_id=user.id, title="You're invited",
            event_date=date.today() - timedelta(days=700),
        )
        s.add(invitation)
        s.add(InvitationGuest(id=uuid.uuid4(), invitation_id=invitation.id,
                              name="Priya Nair", phone="+919911223344",
                              email="priya@example.com"))

        # Media - with a storage id, so the honest-failure path is exercised.
        s.add(Image(id=uuid.uuid4(), owner_id=user.id,
                    url="https://res.cloudinary.com/d/image/upload/v1/tyohaar/a.jpg",
                    storage_path="tyohaar/a", storage_public_id="tyohaar/a",
                    storage_provider="cloudinary", file_size_bytes=1024,
                    mime_type="image/jpeg", width=800, height=600,
                    usage=MediaUsage.BOOKING_EVIDENCE))
        s.add(Video(id=uuid.uuid4(), owner_id=user.id,
                    url="https://res.cloudinary.com/d/video/upload/v1/tyohaar/b.mp4",
                    storage_path="tyohaar/b", storage_public_id="tyohaar/b",
                    storage_provider="cloudinary", file_size_bytes=2048,
                    mime_type="video/mp4", duration_seconds=12,
                    usage=MediaUsage.BOOKING_EVIDENCE))

        booking = Booking(
            id=uuid.uuid4(), booking_number=f"BK-{uuid.uuid4().hex[:8]}",
            customer_id=user.id, celebration_id=booked.id, package_id=package.id,
            recipient_name="Asha Verma", recipient_phone="+919812345678",
            scheduled_date=date.today() - timedelta(days=700),
            booking_type=BookingType.PACKAGE, booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.COMPLETED,
            special_instructions="Call on arrival: 9812345678",
        )
        s.add(booking)

        payment = Payment(
            id=uuid.uuid4(), payment_number=f"PY-{uuid.uuid4().hex[:8]}",
            booking_id=booking.id, payer_id=user.id,
            subtotal=Decimal("15000.00"), final_amount=Decimal("15000.00"),
        )
        s.add(payment)
        s.add(Transaction(
            id=uuid.uuid4(), transaction_number=f"TX-{uuid.uuid4().hex[:8]}",
            transaction_type=TransactionType.PAYMENT, direction=TransactionDirection.CREDIT,
            amount=Decimal("15000.00"), payer_type=PartyType.CUSTOMER, payer_id=user.id,
            payee_type=PartyType.PLATFORM, transacted_at=datetime.now(tz=timezone.utc),
            description="Asha Verma paid for anniversary",
        ))

        s.add(PackageReview(id=uuid.uuid4(), package_id=package.id, customer_id=user.id,
                            rating=5, title="Lovely", body="Superb work, call me on 9812345678"))

        ticket = SupportTicket(
            id=uuid.uuid4(), ticket_number=f"TK-{uuid.uuid4().hex[:8]}",
            customer_id=user.id, category=TicketCategory.BOOKING,
            subject="Timing change", description="Please shift to 7pm, my number is 9812345678",
        )
        s.add(ticket)
        s.add(SupportMessage(id=uuid.uuid4(), ticket_id=ticket.id,
                             sender_role=SupportSenderRole.CUSTOMER, body="Any update?"))

        await s.commit()

        ids = {
            "user": user.id, "booked": booked.id, "unbooked": unbooked.id,
            "booking": booking.id, "payment": payment.id, "package": package.id,
            "invitation": invitation.id,
        }
    return ids


# -- Verification --------------------------------------------------------------


async def main() -> int:
    if not URL:
        sys.exit("TEST_DATABASE_URL is not set.")
    assert_disposable(URL)

    from app.db.session import _build_engine_args

    url, connect_args = _build_engine_args(URL)
    engine = create_async_engine(url, connect_args=connect_args)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    print("schema built\n")

    service = DeletionService(sf)

    # == Stage 1 - realistic user ==============================================
    print("-- building user --")
    ids = await build_user(sf)
    uid = ids["user"]
    print(f"  created user {uid}\n")

    # == Stage 2 - Day 0 =======================================================
    print("-- Day 0: request + deactivation --")
    req = await service.request_deletion(user_id=uid)
    async with sf() as s:
        u = await s.get(User, uid)
        check("Day 0 deactivates the account",
              u.account_status == AccountStatus.DEACTIVATED)
        check("Day 0 preserves data (nothing destroyed yet)", u.full_name == "Asha Verma")
        devices = (await s.execute(select(UserDevice).where(UserDevice.user_id == uid))).scalars().all()
        check("Day 0 revokes device/push registrations", devices == [],
              f"{len(devices)} device rows remain")
    check("request is RECOVERABLE", req.status == DeletionRequestStatus.RECOVERABLE)
    check("no raw identifier stored on the request",
          "9812345678" not in req.identifier_hash and "asha" not in req.identifier_hash.lower())

    # == Stage 3 - recovery window =============================================
    print("\n-- recovery window --")
    due_now = await service.find_due()
    check("inside the window the request is not due", req.id not in due_now)
    future = datetime.now(tz=timezone.utc) + timedelta(days=15)
    check("after 14 days the request becomes due", req.id in await service.find_due(now=future))

    # == Stage 4 - honest failure without Cloudinary ===========================
    print("\n-- purge with Cloudinary unavailable (honesty check) --")
    result = await service.purge_request(request_id=req.id)
    check("unreachable storage yields INCOMPLETE, not PURGED",
          result.status == DeletionRequestStatus.INCOMPLETE,
          f"status={result.status.value}")
    async with sf() as s:
        imgs = (await s.execute(select(Image).where(Image.owner_id == uid))).scalars().all()
        check("media rows are RETAINED when their objects could not be deleted",
              len(imgs) > 0, f"{len(imgs)} image rows kept (pointer preserved)")

    # == Stage 5 - retry with storage working ==================================
    print("\n-- retry with storage stubbed as reachable --")
    from app.services.media import cloudinary_client
    from app.services.deletion.handlers import external as ext_handler

    destroyed: list[str] = []

    async def _stub(public_id: str, *, resource_type: str = "image") -> bool:
        destroyed.append(f"{resource_type}:{public_id}")
        return True

    ext_handler.cloudinary_client.destroy_asset = _stub  # type: ignore[assignment]

    async with sf() as s:
        # Clear the unresolved markers the failed run recorded, as a real
        # operator would after fixing credentials.
        await s.execute(text("DELETE FROM unresolved_media_assets"))
        await s.commit()

    retried = await service.purge_request(request_id=req.id)
    check("retry after fixing storage reaches PURGED",
          retried.status == DeletionRequestStatus.PURGED, f"status={retried.status.value}")
    check("storage objects were actually destroyed", len(destroyed) >= 2,
          f"destroyed={destroyed}")
    check("completed request no longer names the person", retried.user_id is None)

    # == Stage 6 - the assertions that matter ==================================
    print("\n-- post-purge verification --")
    async with sf() as s:
        u = await s.get(User, uid)
        check("tombstone row survives (RESTRICT FKs require it)", u is not None)
        check("user PII erased",
              u.email is None and u.full_name is None and u.first_name is None
              and u.last_name is None and u.password_hash is None
              and u.phone.startswith("x") and len(u.phone) == 15,
              f"phone={u.phone!r}")

        prof = (await s.execute(select(UserProfile).where(UserProfile.user_id == uid))).scalars().all()
        addr = (await s.execute(select(UserAddress).where(UserAddress.user_id == uid))).scalars().all()
        check("profile deleted (CASCADE)", prof == [])
        check("addresses deleted (CASCADE)", addr == [])

        booked = await s.get(Celebration, ids["booked"])
        unbooked = await s.get(Celebration, ids["unbooked"])
        check("booked celebration SANITISED, not deleted",
              booked is not None and booked.title is None and booked.venue_address is None
              and booked.latitude is None and booked.special_instructions is None,
              "row survives with personal fields cleared")
        check("booked celebration keeps structural context",
              booked is not None and booked.occasion_id is not None
              and booked.celebration_date is not None)
        check("unbooked celebration DELETED", unbooked is None)

        bk = await s.get(Booking, ids["booking"])
        check("booking retained (financial record)", bk is not None)
        check("booking PII scrubbed",
              bk is not None and bk.recipient_phone is None and bk.recipient_name is None
              and bk.special_instructions is None)

        pay = await s.get(Payment, ids["payment"])
        check("payment retained (financial record)", pay is not None)

        tx = (await s.execute(select(Transaction).where(Transaction.payer_id == uid))).scalars().all()
        check("transaction free text scrubbed",
              all(t.description is None for t in tx), f"{len(tx)} transactions")

        cg = (await s.execute(select(CelebrationGuest))).scalars().all()
        ig = (await s.execute(select(InvitationGuest))).scalars().all()
        check("celebration guest PII purged with the host", cg == [],
              f"{len(cg)} guest rows remain")
        check("invitation guest PII purged with the host", ig == [],
              f"{len(ig)} guest rows remain")

        tickets = (await s.execute(select(SupportTicket).where(SupportTicket.customer_id == uid))).scalars().all()
        check("support tickets purged", tickets == [])

        memberships = (await s.execute(text(
            "SELECT count(*) FROM user_memberships WHERE user_id = :u"), {"u": uid})).scalar()
        check("membership records purged", memberships == 0)

        rev = (await s.execute(select(PackageReview).where(PackageReview.customer_id == uid))).scalars().all()
        check("review retained under the configured 'tombstone' strategy", len(rev) == 1)
        check("review free text scrubbed of contact details",
              all("9812345678" not in (r.body or "") for r in rev),
              (rev[0].body if rev else ""))

        imgs = (await s.execute(select(Image).where(Image.owner_id == uid))).scalars().all()
        vids = (await s.execute(select(Video).where(Video.owner_id == uid))).scalars().all()
        check("media rows removed once objects were destroyed", imgs == [] and vids == [])

        report = str(retried.purge_report)
        check("purge report contains no personal data",
              "9812345678" not in report and "Asha" not in report
              and "asha.verma@example.com" not in report)

    # == Stage 7 - idempotency =================================================
    print("\n-- repeat execution --")
    again = await service.purge_request(request_id=req.id)
    check("repeat purge is safe and stays PURGED",
          again.status == DeletionRequestStatus.PURGED)

    # == Stage 8 - guest clock independence ====================================
    print("\n-- guest clock (independent of accounts) --")
    from app.services.deletion.handlers.guests import purge_expired_guest_pii

    async with sf() as s:
        occ = (await s.execute(select(Occasion))).scalars().first()
        host = User(id=uuid.uuid4(), phone="+919700000001", full_name="Active Host",
                    role=UserRole.CUSTOMER, user_type=UserType.INDIVIDUAL,
                    account_status=AccountStatus.ACTIVE)
        s.add(host)
        old = Celebration(id=uuid.uuid4(), customer_id=host.id, occasion_id=occ.id,
                          title="Old Diwali", celebration_date=date.today() - timedelta(days=900))
        recent = Celebration(id=uuid.uuid4(), customer_id=host.id, occasion_id=occ.id,
                             title="Recent Diwali", celebration_date=date.today() - timedelta(days=30))
        s.add_all([old, recent])
        s.add(CelebrationGuest(id=uuid.uuid4(), celebration_id=old.id, name="Old Guest",
                               phone="+919700000002"))
        s.add(CelebrationGuest(id=uuid.uuid4(), celebration_id=recent.id, name="Recent Guest",
                               phone="+919700000003"))
        await s.commit()

    async with sf() as s:
        counts = await purge_expired_guest_pii(s)
        await s.commit()

    async with sf() as s:
        remaining = (await s.execute(select(CelebrationGuest))).scalars().all()
        names = {g.name for g in remaining}
        check("guest past the event window purged while host stays active",
              "Old Guest" not in names, f"purged={counts}")
        check("guest inside the window retained", "Recent Guest" in names)
        host_row = (await s.execute(select(User).where(User.full_name == "Active Host"))).scalars().first()
        check("active host NOT deleted by the guest sweep",
              host_row is not None and host_row.account_status == AccountStatus.ACTIVE)

    await engine.dispose()

    # -- Summary ---------------------------------------------------------------
    failed = [r for r in RESULTS if not r[1]]
    print("\n" + "=" * 62)
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("\nFAILURES:")
        for name, _, detail in failed:
            print(f"  - {name}  {detail}")
    print("=" * 62)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
