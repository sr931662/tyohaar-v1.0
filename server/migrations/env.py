import asyncio
import os
import ssl as _ssl
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load all models so Alembic can detect them
from app.models.base import Base
import app.models  # noqa: F401

target_metadata = Base.metadata

# Load DATABASE_URL via pydantic-settings (reads .env automatically).
# Fallback to raw env var so CI/CD pipelines that inject the var directly also work.
try:
    from app.core.config import settings as _settings
    _raw_url: str = _settings.DATABASE_URL
except Exception:
    _raw_url = os.environ.get("DATABASE_URL", "")

if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Create a .env file in the server/ directory with DATABASE_URL=postgresql+asyncpg://..."
    )

# Async engine needs postgresql+asyncpg://; Alembic offline mode needs postgresql://
if _raw_url.startswith("postgresql://"):
    _async_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    _sync_url = _raw_url
elif _raw_url.startswith("postgresql+asyncpg://"):
    _async_url = _raw_url
    _sync_url = _raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
else:
    _async_url = _raw_url
    _sync_url = _raw_url

config.set_main_option("sqlalchemy.url", _sync_url)


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def _asyncpg_engine_kwargs(url: str) -> tuple[str, dict]:
    """
    asyncpg does not accept 'sslmode' as a connect keyword.
    Strip it from the URL query string and convert to a proper ssl connect_arg.
    Returns (clean_url, connect_args).
    """
    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}
    sslmode = params.pop("sslmode", None)
    clean_url = urlunparse(parsed._replace(query=urlencode(params)))

    connect_args: dict = {}
    if sslmode in ("require", "verify-ca", "verify-full"):
        ctx = _ssl.create_default_context()
        if sslmode == "require":
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE
        connect_args["ssl"] = ctx
    elif sslmode == "disable":
        connect_args["ssl"] = False

    return clean_url, connect_args


async def run_async_migrations() -> None:
    clean_url, connect_args = _asyncpg_engine_kwargs(_async_url)
    connectable = create_async_engine(
        clean_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
