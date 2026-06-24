"""
Seed script — creates the super admin role and a superadmin account.

Run from the server/ directory:
    python scripts/seed_admin.py

Environment variables (or .env file):
    ADMIN_PHONE    — E.164 phone number  e.g. +919876543210
    ADMIN_EMAIL    — work email          e.g. admin@tyohaar.com
    ADMIN_NAME     — full name           e.g. "Superadmin"

If the role or user already exists the script is idempotent (skips creation).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Make sure `app` is importable when running from server/
sys.path.insert(0, str(Path(__file__).parent.parent))

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

# ── Config ────────────────────────────────────────────────────────────────────

PHONE    = os.getenv("ADMIN_PHONE", "+919999999999")
EMAIL    = os.getenv("ADMIN_EMAIL", "admin@tyohaar.com")
NAME     = os.getenv("ADMIN_NAME", "Superadmin")
PASSWORD = os.getenv("ADMIN_PASSWORD", "")

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
        if PASSWORD and not user.password_hash:
            user.password_hash = hash_admin_password(PASSWORD)
            print("  [~] Set password_hash on existing user")
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


async def get_or_create_admin(session, user: User, role: AdminRole) -> Admin:
    result = await session.execute(
        select(Admin).where(Admin.user_id == user.id)
    )
    admin = result.scalar_one_or_none()
    if admin:
        print(f"  [skip] Admin record already exists  (id={admin.id})")
        return admin

    admin = Admin(
        user_id=user.id,
        role_id=role.id,
        employee_id="TYH-001",
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
    print(f"  [+] Admin record created  (id={admin.id})")
    return admin


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
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
        print("Done. No password set — set ADMIN_PASSWORD env var to enable password login.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
