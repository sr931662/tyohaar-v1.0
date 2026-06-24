"""Force-update password_hash for the superadmin user."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update

from app.core.config import settings  # noqa: loads .env
from app.db.session import AsyncSessionLocal
from app.models.users.user import User
from app.services.admin.helpers import hash_admin_password, verify_admin_password

EMAIL = "sr931662@gmail.com"
PASSWORD = input("Enter new password to set: ")


async def main() -> None:
    new_hash = hash_admin_password(PASSWORD)
    print(f"\nSECRET_KEY (first 10 chars): {settings.SECRET_KEY[:10]}...")
    print(f"New hash: {new_hash}")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == EMAIL))
        user = result.scalar_one_or_none()
        if user is None:
            print("ERROR: User not found")
            return

        print(f"Old hash: {user.password_hash}")
        await session.execute(
            update(User).where(User.email == EMAIL).values(password_hash=new_hash)
        )
        await session.commit()
        print("[✓] password_hash updated in DB")

        # Verify
        result = await session.execute(select(User).where(User.email == EMAIL))
        user = result.scalar_one_or_none()
        print(f"Stored now: {user.password_hash}")
        print(f"Match: {verify_admin_password(PASSWORD, user.password_hash or '')}")


if __name__ == "__main__":
    asyncio.run(main())
