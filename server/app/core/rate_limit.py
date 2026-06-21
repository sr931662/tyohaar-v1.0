from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from fastapi import Request

from app.core.constants import (
    AUTH_RATE_LIMIT_REQUESTS,
    AUTH_RATE_LIMIT_WINDOW_SECONDS,
    DEFAULT_RATE_LIMIT_REQUESTS,
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
)


@dataclass(frozen=True)
class RateLimitConfig:
    """Immutable configuration for a single rate-limit rule."""

    requests: int
    window_seconds: int
    key_prefix: str = "rl"


@runtime_checkable
class RateLimiterProtocol(Protocol):
    """
    Interface contract for rate-limiter backends.

    Implement this protocol to plug in Redis, in-memory, or any other
    backend without changing the dependency layer.
    """

    async def is_allowed(self, key: str, config: RateLimitConfig) -> bool:
        """Return True if the request is within the configured limit."""
        ...

    async def remaining(self, key: str, config: RateLimitConfig) -> int:
        """Return the number of remaining calls in the current window."""
        ...

    async def reset_after(self, key: str, config: RateLimitConfig) -> int:
        """Return seconds until the window resets."""
        ...


# ── Pre-built configs ─────────────────────────────────────────────────────────

DEFAULT_RATE_LIMIT = RateLimitConfig(
    requests=DEFAULT_RATE_LIMIT_REQUESTS,
    window_seconds=DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
    key_prefix="rl:api",
)

AUTH_RATE_LIMIT = RateLimitConfig(
    requests=AUTH_RATE_LIMIT_REQUESTS,
    window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    key_prefix="rl:auth",
)


# ── Key derivation helper ─────────────────────────────────────────────────────

def get_rate_limit_key(request: Request, config: RateLimitConfig) -> str:
    """Derive a per-client rate-limit key from the client IP."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    return f"{config.key_prefix}:{client_ip}"
