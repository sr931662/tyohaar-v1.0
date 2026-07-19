from __future__ import annotations

import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _build_engine_args(url: str) -> tuple[str, dict]:
    """
    asyncpg rejects 'sslmode' as a connect keyword (it's a libpq/psycopg2 param).
    Strip it from the URL and convert to an ssl.SSLContext in connect_args.
    """
    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}
    sslmode = params.pop("sslmode", None)
    clean_url = urlunparse(parsed._replace(query=urlencode(params)))

    connect_args: dict = {}
    if sslmode in ("require", "verify-ca", "verify-full"):
        ctx = ssl.create_default_context()
        if sslmode == "require":
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx
    elif sslmode == "disable":
        connect_args["ssl"] = False

    return clean_url, connect_args


_db_url, _connect_args = _build_engine_args(settings.DATABASE_URL)

engine = create_async_engine(
    _db_url,
    echo=False,
    connect_args={
        **_connect_args,
        # Neon's pooled endpoints (and any PgBouncer in transaction mode)
        # multiplex client connections across backend connections, which
        # breaks asyncpg's cached named prepared statements — a statement
        # prepared on one backend is executed on another, failing mid-flush
        # and killing the connection (503 "database error"). The documented
        # SQLAlchemy recipe: disable both statement caches and give every
        # prepared statement a unique name. Harmless (slightly slower) on
        # direct, non-pooled connections.
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    },
    # Managed Postgres closes idle connections and Cloud Run pauses/recycles
    # instances, so pooled connections go stale between requests. pre_ping
    # validates (and transparently replaces) a connection before each use;
    # recycle proactively retires connections older than the idle window.
    pool_pre_ping=True,
    pool_recycle=1800,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
