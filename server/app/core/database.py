from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields one AsyncSession per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> dict[str, Any]:
    """Probe the database and return a health dict for liveness checks."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        return {"status": "unhealthy", "database": str(exc)}


async def ping_database() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def dispose_engine() -> None:
    """Dispose the SQLAlchemy engine connection pool — called on shutdown."""
    await engine.dispose()
