from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import REQUEST_ID_HEADER

logger = logging.getLogger("tyohaar.access")

# Headers that must never appear in log output.
_REDACTED_HEADERS: frozenset[str] = frozenset(
    {"authorization", "cookie", "x-api-key", "x-auth-token"}
)

# Body field names that must never appear in log output.
# (Body logging is not implemented here, but the constant documents the policy.)
_REDACTED_FIELDS: frozenset[str] = frozenset(
    {"password", "otp", "pin", "secret", "token", "refresh_token"}
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured access log middleware.

    Logs one line per request after the response is sent:

        METHOD /path STATUS_CODE XXX.Xms [request-id]

    Security guarantees:
        - Authorization header is NEVER logged.
        - Cookie header is NEVER logged.
        - OTP / password fields are NEVER logged (body logging is not performed).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        # request_id is set by RequestIDMiddleware which runs before us.
        request_id: str = getattr(
            request.state, "request_id", request.headers.get(REQUEST_ID_HEADER, "-")
        )

        response: Response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %d %.1fms [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
