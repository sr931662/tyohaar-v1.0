from __future__ import annotations

import logging
import uuid

from fastapi import Request

from app.core.constants import CORRELATION_ID_HEADER, REQUEST_ID_HEADER


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging with a standard format. Called once at startup."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def get_request_logger(request: Request) -> logging.LoggerAdapter:
    """
    FastAPI dependency — returns a LoggerAdapter enriched with per-request
    context (request_id, correlation_id, method, path).
    """
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
    correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id

    logger = logging.getLogger("tyohaar.api")
    return logging.LoggerAdapter(
        logger,
        extra={
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
        },
    )
