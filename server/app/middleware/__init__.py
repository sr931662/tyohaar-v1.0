"""
Tyohaar Middleware Layer
========================

Production middleware stack for the Tyohaar API.

Middleware and their execution order (outermost → innermost):
    TrustedHostMiddleware   — reject requests from unrecognised Host headers
    CORSMiddleware          — handle preflight + CORS response headers
    RequestIDMiddleware     — assign / propagate X-Request-ID
    LoggingMiddleware       — structured access log (method, path, status, ms)
    SecurityHeadersMiddleware — add security response headers
    GZipMiddleware          — compress eligible response bodies

Public exports:
    LoggingMiddleware
    RequestIDMiddleware
    SecurityHeadersMiddleware
"""

from app.middleware.logging import LoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware

__all__ = [
    "LoggingMiddleware",
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
]
