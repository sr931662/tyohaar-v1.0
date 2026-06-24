"""Quick script to unlock a locked admin account."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update

from app.core.config import settings  # noqa: loads .env
from app.db.session import AsyncSessionLocal
from app.models.admin.admin import Admin
from app.models.users.user import User


async def main() -> None:
    email = "sr931662@gmail.com"
    print(f"\nUnlocking admin for email: {email}")

    async with AsyncSessionLocal() as session:
        # Find user by email
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            print("  [ERROR] User not found.")
            return

        # Find admin by user_id
        result = await session.execute(select(Admin).where(Admin.user_id == user.id))
        admin = result.scalar_one_or_none()
        if admin is None:
            print("  [ERROR] Admin record not found.")
            return

        print(f"  Found admin  id={admin.id}  failed_login_count={admin.failed_login_count}  locked_until={admin.account_locked_until}")

        await session.execute(
            update(Admin)
            .where(Admin.id == admin.id)
            .values(failed_login_count=0, account_locked_until=None)
        )
        await session.commit()
        print("  [✓] Admin unlocked successfully.")


if __name__ == "__main__":
    asyncio.run(main())
