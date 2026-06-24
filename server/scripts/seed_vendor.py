"""
Seed script — create a vendor profile from interactive terminal input.

Run from the server/ directory:
    python scripts/seed_vendor.py

Steps:
  1. Prompts for user + business details
  2. Creates (or reuses) a User with role=VENDOR
  3. Creates a Vendor record
  4. Creates a VendorProfile record
"""

from __future__ import annotations

import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.config import settings  # noqa: loads .env
from app.services.admin.helpers import hash_admin_password
from app.db.session import AsyncSessionLocal
from app.models.enums import (
    AccountStatus,
    LoginMethod,
    UserRole,
    UserType,
    VendorStatus,
    VendorType,
    VendorVerificationStatus,
    VerificationStatus,
)
from app.models.users.user import User
from app.models.vendors.vendor import Vendor
from app.models.vendors.vendor_profile import VendorProfile


# ── Pretty prompt helpers ─────────────────────────────────────────────────────

def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val or default


def ask_choice(prompt: str, choices: list[str], default: str = "") -> str:
    print(f"\n  {prompt}")
    for i, c in enumerate(choices, 1):
        marker = " *" if c == default else ""
        print(f"    {i:2}. {c}{marker}")
    while True:
        raw = input(f"  Choose [1-{len(choices)}]: ").strip()
        if raw == "" and default:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        print("     Invalid choice. Try again.")


def ask_int(prompt: str, default: int | None = None, min_val: int = 0, max_val: int = 9999) -> int | None:
    suffix = f" [{default}]" if default is not None else " [skip]"
    while True:
        raw = input(f"  {prompt}{suffix}: ").strip()
        if raw == "":
            return default
        if raw.isdigit() and min_val <= int(raw) <= max_val:
            return int(raw)
        print(f"     Enter a number between {min_val} and {max_val}.")


def divider(title: str = "") -> None:
    width = 54
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{'-' * pad} {title} {'-' * pad}")
    else:
        print(f"\n{'-' * width}")


# ── Collect details ───────────────────────────────────────────────────────────

def collect_details() -> dict:
    print("\n" + "=" * 56)
    print("  Tyohaar -- Vendor Seed Script")
    print("  Fill in the details below. Press Enter to skip optional fields.")
    print("=" * 56)

    divider("USER ACCOUNT")
    phone = ask("Mobile number (E.164 format, e.g. +919876543210)", "+91")
    if not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0")
    email = ask("Email address (used for login)")
    full_name = ask("Full name")
    password = getpass.getpass("  Login password: ")
    if not password:
        print("  [!] No password entered — vendor won't be able to log in via email.")

    divider("BUSINESS IDENTITY")
    vendor_types = [v.value for v in VendorType]
    vendor_type = ask_choice("Vendor type", vendor_types, VendorType.DECORATOR.value)
    business_name = ask("Business / brand name")
    legal_name = ask("Legal entity name (optional)")
    gst_number = ask("GST number (optional)").upper() or None
    pan_number = ask("PAN number (optional)").upper() or None
    years_exp = ask_int("Years of experience (optional)", min_val=0, max_val=100)
    established_year = ask_int("Year established (optional)", min_val=1900, max_val=2030)
    service_radius = ask_int("Service radius in km (optional)", min_val=0, max_val=5000)

    divider("PROFILE")
    tagline = ask("Tagline / slogan (optional)")
    about = ask("Short about / description (optional)")

    return {
        "phone": phone,
        "email": email or None,
        "full_name": full_name or None,
        "password": password or None,
        "vendor_type": vendor_type,
        "business_name": business_name,
        "legal_name": legal_name or None,
        "gst_number": gst_number,
        "pan_number": pan_number,
        "years_of_experience": years_exp,
        "established_year": established_year,
        "service_radius_km": service_radius,
        "tagline": tagline or None,
        "about": about or None,
    }


# ── DB operations ─────────────────────────────────────────────────────────────

async def get_or_create_user(session, d: dict) -> User:
    result = await session.execute(select(User).where(User.phone == d["phone"]))
    user = result.scalar_one_or_none()

    if user:
        print(f"\n  [skip] User already exists  (id={user.id}  phone={d['phone']})")
        if user.role != UserRole.VENDOR:
            user.role = UserRole.VENDOR
            print("  [~] Role updated -> VENDOR")
        if d.get("password"):
            user.password_hash = hash_admin_password(d["password"])
            print("  [~] Password updated")
        return user

    user = User(
        phone=d["phone"],
        email=d["email"],
        full_name=d["full_name"],
        role=UserRole.VENDOR,
        user_type=UserType.BUSINESS,
        account_status=AccountStatus.ACTIVE,
        verification_status=VerificationStatus.VERIFIED,
        primary_login_provider=LoginMethod.OTP_PHONE,
        phone_verified=True,
        email_verified=bool(d["email"]),
        mfa_enabled=False,
        password_hash=hash_admin_password(d["password"]) if d.get("password") else None,
    )
    session.add(user)
    await session.flush()
    print(f"\n  [+] User created  (id={user.id})")
    return user


async def get_or_create_vendor(session, user: User, d: dict) -> Vendor:
    result = await session.execute(select(Vendor).where(Vendor.user_id == user.id))
    vendor = result.scalar_one_or_none()

    if vendor:
        print(f"  [skip] Vendor already exists  (id={vendor.id})")
        return vendor

    vendor = Vendor(
        user_id=user.id,
        business_name=d["business_name"],
        legal_name=d["legal_name"],
        vendor_type=d["vendor_type"],
        gst_number=d["gst_number"],
        pan_number=d["pan_number"],
        years_of_experience=d["years_of_experience"],
        established_year=d["established_year"],
        service_radius_km=d["service_radius_km"],
        status=VendorStatus.PENDING,
        verification_status=VendorVerificationStatus.UNVERIFIED,
        average_rating=0.0,
        review_count=0,
        completion_count=0,
        cancellation_count=0,
        acceptance_rate_pct=100.0,
        priority_score=50,
    )
    session.add(vendor)
    await session.flush()
    print(f"  [+] Vendor created  (id={vendor.id})")
    return vendor


async def get_or_create_profile(session, vendor: Vendor, d: dict) -> VendorProfile:
    result = await session.execute(select(VendorProfile).where(VendorProfile.vendor_id == vendor.id))
    profile = result.scalar_one_or_none()

    if profile:
        print(f"  [skip] VendorProfile already exists  (id={profile.id})")
        return profile

    profile = VendorProfile(
        vendor_id=vendor.id,
        tagline=d["tagline"],
        about=d["about"],
    )
    session.add(profile)
    await session.flush()
    print(f"  [+] VendorProfile created  (id={profile.id})")
    return profile


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    details = collect_details()

    divider("CONFIRM")
    print(f"  Phone        : {details['phone']}")
    print(f"  Email        : {details['email'] or '—'}")
    print(f"  Name         : {details['full_name'] or '—'}")
    print(f"  Business     : {details['business_name']}")
    print(f"  Type         : {details['vendor_type']}")
    if details["gst_number"]:
        print(f"  GST          : {details['gst_number']}")
    if details["pan_number"]:
        print(f"  PAN          : {details['pan_number']}")

    confirm = input("\n  Create vendor with these details? [Y/n]: ").strip().lower()
    if confirm == "n":
        print("  Aborted.")
        sys.exit(0)

    print()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            user    = await get_or_create_user(session, details)
            vendor  = await get_or_create_vendor(session, user, details)
            profile = await get_or_create_profile(session, vendor, details)

    print()
    print("=" * 56)
    print("  Done!")
    print(f"  User ID   : {user.id}")
    print(f"  Vendor ID : {vendor.id}")
    print(f"  Login URL : /vendor/login  (phone OTP: {details['phone']})")
    print("=" * 56)
    print()


if __name__ == "__main__":
    asyncio.run(main())
