"""
Tyohaar API — Development Entry Point
======================================

Run locally:

    python run.py

Production deployments should call uvicorn directly (or via gunicorn):

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

Environment variables:
    HOST        Bind address          (default: 0.0.0.0)
    PORT        Bind port             (default: 8000)
    RELOAD      Hot-reload on change  (default: true for dev, false otherwise)
    WORKERS     Process count         (default: 1 in dev / 4 in prod)
    LOG_LEVEL   Uvicorn log level     (default: info)
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    try:
        import uvicorn
    except ImportError:
        print("uvicorn is not installed. Run: pip install uvicorn[standard]", file=sys.stderr)
        sys.exit(1)

    # Determine environment from the ENVIRONMENT env-var (before loading settings
    # so we can bootstrap correctly even without a full .env file).
    env = os.environ.get("ENVIRONMENT", "development").lower()
    is_production = env == "production"

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", str(not is_production)).lower() == "true"
    workers = int(os.environ.get("WORKERS", "1" if not is_production else "4"))
    log_level = os.environ.get("LOG_LEVEL", "info").lower()

    # uvicorn does not support --reload with multiple workers.
    if reload and workers > 1:
        workers = 1

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
        access_log=False,       # our LoggingMiddleware handles access logging
        server_header=False,    # do not expose server version in response headers
        date_header=False,      # reduce response header surface
    )


if __name__ == "__main__":
    main()
