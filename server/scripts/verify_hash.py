"""Debug: compare stored hash vs locally computed hash."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.users.user import User
from app.services.admin.helpers import hash_admin_password, verify_admin_password

EMAIL = "sr931662@gmail.com"
PASSWORD = input("Enter password to verify: ")


async def main() -> None:
    print(f"\nSECRET_KEY (first 10 chars): {settings.SECRET_KEY[:10]}...")
    computed = hash_admin_password(PASSWORD)
    print(f"Computed hash: {computed}")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == EMAIL))
        user = result.scalar_one_or_none()
        if user is None:
            print("ERROR: User not found in DB")
            return
        stored = user.password_hash
        print(f"Stored hash:   {stored}")
        print(f"\nMatch: {computed == stored}")
        print(f"verify_admin_password result: {verify_admin_password(PASSWORD, stored or '')}")


if __name__ == "__main__":
    asyncio.run(main())
