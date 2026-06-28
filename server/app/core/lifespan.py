from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import check_database_health, dispose_engine
from app.core.logging import configure_logging

logger = logging.getLogger("tyohaar.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.

    Startup
    -------
    1. Configure root logging.
    2. Probe the database and log the result.

    Shutdown
    --------
    1. Dispose the SQLAlchemy engine connection pool.
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    configure_logging()
    logger.info("Starting %s…", app.title)

    health = await check_database_health()
    if health["status"] == "healthy":
        logger.info("Database connection verified.")
    else:
        logger.critical("Database unreachable on startup: %s", health["database"])

    # Run pending Alembic migrations so schema is always in sync with code.
    try:
        import asyncio
        import pathlib
        from alembic import command
        from alembic.config import Config as AlembicConfig

        _alembic_ini = pathlib.Path(__file__).parent.parent.parent / "alembic.ini"

        def _run_migrations() -> None:
            cfg = AlembicConfig(str(_alembic_ini))
            command.upgrade(cfg, "head")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run_migrations)
        logger.info("Alembic migrations applied.")
    except Exception as exc:
        logger.error("Alembic migration failed on startup: %s", exc, exc_info=True)

    logger.info("%s is ready to serve requests.", app.title)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down %s…", app.title)
    await dispose_engine()
    logger.info("Engine disposed. Goodbye.")
