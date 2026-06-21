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

    logger.info("%s is ready to serve requests.", app.title)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down %s…", app.title)
    await dispose_engine()
    logger.info("Engine disposed. Goodbye.")
