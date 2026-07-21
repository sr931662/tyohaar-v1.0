"""
Seed script — creates the super admin role and a superadmin account.

Run from anywhere (server/ or server/scripts/):
    python scripts/seed_admin.py
    python seed_admin.py   (from within scripts/)

Prompts interactively for the admin's phone/email/name/password — nothing
is read from environment variables. Press Enter on phone/email/name to
accept the shown default; the password prompt is hidden (getpass) and has
no default (leave blank to create the account without password login).

If the role or user already exists the script is idempotent (skips creation).
"""

from __future__ import annotations

import asyncio
import getpass
import sys
from pathlib import Path

# Make sure `app` is importable regardless of which directory this is run from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import settings  # noqa: loads .env
from app.services.admin.helpers import hash_admin_password
from app.db.session import AsyncSessionLocal
from app.models.admin.admin import Admin
from app.models.admin.role import AdminRole
from app.models.enums import (
    AccountStatus,
    AdminDepartment,
    AdminStatus,
    LoginMethod,
    UserRole,
    UserType,
    VerificationStatus,
)
from app.models.users.user import User

# ── Config (filled in interactively by prompt_for_credentials()) ─────────────

PHONE = ""
EMAIL = ""
NAME = ""
PASSWORD = ""


def prompt_for_credentials() -> None:
    """Collects admin details from the terminal. Called once at startup."""
    global PHONE, EMAIL, NAME, PASSWORD

    def ask(label: str, default: str) -> str:
        raw = input(f"{label} [{default}]: ").strip()
        return raw or default

    print("\n=== Enter Superadmin Details ===")
    PHONE = ask("Phone (E.164, e.g. +919876543210)", "+919999999999")
    EMAIL = ask("Email", "admin@tyohaar.com")
    NAME = ask("Full name", "Superadmin")
    PASSWORD = getpass.getpass(
        "Password (leave blank to skip password login, input hidden): "
    ).strip()

SUPERADMIN_ROLE = {
    "name": "Super Admin",
    "slug": "super_admin",
    "description": "Full platform access. Bypasses all permission checks.",
    "is_system": True,
    "is_super_admin": True,
    "is_active": True,
    "priority_rank": 1,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

async def get_or_create_role(session) -> AdminRole:
    result = await session.execute(
        select(AdminRole).where(AdminRole.slug == "super_admin")
    )
    role = result.scalar_one_or_none()
    if role:
        print(f"  [skip] AdminRole 'super_admin' already exists  (id={role.id})")
        return role

    role = AdminRole(**SUPERADMIN_ROLE)
    session.add(role)
    await session.flush()
    print(f"  [+] AdminRole 'super_admin' created  (id={role.id})")
    return role


async def get_or_create_user(session) -> User:
    result = await session.execute(
        select(User).where(User.phone == PHONE)
    )
    user = result.scalar_one_or_none()
    if user:
        print(f"  [skip] User already exists  (id={user.id}  phone={PHONE})")
        if user.role != UserRole.SUPER_ADMIN:
            user.role = UserRole.SUPER_ADMIN
            user.account_status = AccountStatus.ACTIVE
            user.email_verified = True
            print("  [~] Upgraded user role -> SUPER_ADMIN")
        if PASSWORD:
            user.password_hash = hash_admin_password(PASSWORD)
            print("  [~] Updated password_hash (re-hashed with current SECRET_KEY)")
        return user

    user = User(
        phone=PHONE,
        email=EMAIL,
        full_name=NAME,
        role=UserRole.SUPER_ADMIN,
        user_type=UserType.INDIVIDUAL,
        account_status=AccountStatus.ACTIVE,
        verification_status=VerificationStatus.VERIFIED,
        primary_login_provider=LoginMethod.OTP_EMAIL,
        phone_verified=True,
        email_verified=True,
        mfa_enabled=False,
        password_hash=hash_admin_password(PASSWORD) if PASSWORD else None,
    )
    session.add(user)
    await session.flush()
    print(f"  [+] User created  (id={user.id}  phone={PHONE}  email={EMAIL})")
    return user


async def next_employee_id(session) -> str:
    """
    TYH-001, TYH-002, ... — scans existing employee_ids (including soft-
    deleted admins, since uq_admins_employee_id doesn't exempt them) and
    returns the next free one, so seeding a second/third admin doesn't
    collide with an earlier run's TYH-001.
    """
    result = await session.execute(
        select(Admin.employee_id).where(Admin.employee_id.like("TYH-%"))
    )
    used_numbers = set()
    for (employee_id,) in result.all():
        suffix = employee_id.rsplit("-", 1)[-1]
        if suffix.isdigit():
            used_numbers.add(int(suffix))

    next_number = 1
    while next_number in used_numbers:
        next_number += 1
    return f"TYH-{next_number:03d}"


async def get_or_create_admin(session, user: User, role: AdminRole) -> Admin:
    result = await session.execute(
        select(Admin).where(Admin.user_id == user.id)
    )
    admin = result.scalar_one_or_none()
    if admin:
        print(f"  [skip] Admin record already exists  (id={admin.id})")
        return admin

    employee_id = await next_employee_id(session)
    admin = Admin(
        user_id=user.id,
        role_id=role.id,
        employee_id=employee_id,
        department=AdminDepartment.MANAGEMENT,
        designation="Superadmin",
        work_email=EMAIL,
        admin_status=AdminStatus.ACTIVE,
        mfa_enforced=False,
        can_impersonate=True,
        can_access_financials=True,
        can_export_data=True,
    )
    session.add(admin)
    await session.flush()
    print(f"  [+] Admin record created  (id={admin.id}  employee_id={employee_id})")
    return admin


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    prompt_for_credentials()

    print("\n=== Tyohaar -- Superadmin Seed ===")
    print(f"  Phone : {PHONE}")
    print(f"  Email : {EMAIL}")
    print(f"  Name  : {NAME}")
    print()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            role  = await get_or_create_role(session)
            user  = await get_or_create_user(session)
            admin = await get_or_create_admin(session, user, role)

    print()
    if PASSWORD:
        print("Done. Admin password set. Login via:")
        print('POST /api/v1/admin/auth/login  { "email": "' + EMAIL + '", "password": "****" }')
    else:
        print("Done. No password set — re-run and enter a password to enable password login.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
