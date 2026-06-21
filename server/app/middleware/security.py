from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

# HSTS header value — 1 year, include subdomains.
_HSTS_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security-oriented response headers to every outgoing response.

    Headers always added:
        X-Content-Type-Options: nosniff
        X-Frame-Options: DENY
        Referrer-Policy: strict-origin-when-cross-origin
        Permissions-Policy: geolocation=(), microphone=(), camera=()

    Header added only in production (HTTPS assumed):
        Strict-Transport-Security: max-age=31536000; includeSubDomains
    """

    def __init__(self, app, **kwargs) -> None:
        super().__init__(app, **kwargs)
        self._is_production = settings.is_production

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        if self._is_production:
            response.headers["Strict-Transport-Security"] = _HSTS_VALUE

        return response
