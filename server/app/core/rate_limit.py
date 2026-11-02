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

def client_ip(request: Request) -> str:
    """
    The caller's IP for rate limiting.

    X-Forwarded-For is "<whatever the client sent>, <added by each proxy>",
    so its FIRST entry is attacker-controlled: keying on it let anyone dodge a
    per-IP limit by sending a fresh fake address each time. The trustworthy
    entry is the one our own proxy appended, counted from the right:
    TRUSTED_PROXY_HOPS = 1 for Cloud Run's front end (the default), 2 behind
    an extra load balancer.
    """
    from app.core.config import settings

    forwarded = [p.strip() for p in request.headers.get("X-Forwarded-For", "").split(",") if p.strip()]
    hops = max(1, settings.TRUSTED_PROXY_HOPS)
    if len(forwarded) >= hops:
        return forwarded[-hops]
    return request.client.host if request.client else "unknown"


def get_rate_limit_key(request: Request, config: RateLimitConfig) -> str:
    """Derive a per-client rate-limit key from the client IP."""
    return f"{config.key_prefix}:{client_ip(request)}"


# ── In-memory backend ─────────────────────────────────────────────────────────

class InMemoryRateLimiter:
    """
    Sliding-window limiter held in process memory.

    Adequate for a single API instance (and as a per-instance ceiling when
    several run): limits are enforced per worker, not cluster-wide. Swap in a
    Redis-backed RateLimiterProtocol implementation to share counters.
    """

    _MAX_KEYS = 50_000  # bound memory under a key-spraying client

    def __init__(self) -> None:
        import asyncio
        from collections import deque

        self._hits: dict[str, deque[float]] = {}
        self._deque = deque
        self._lock = asyncio.Lock()

    def _window(self, key: str, config: RateLimitConfig, now: float):
        hits = self._hits.get(key)
        if hits is None:
            if len(self._hits) >= self._MAX_KEYS:
                self._hits.clear()
            hits = self._hits[key] = self._deque()
        cutoff = now - config.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        return hits

    async def hit(self, key: str, config: RateLimitConfig) -> bool:
        """Record one call; True if it is within the limit."""
        import time

        async with self._lock:
            now = time.monotonic()
            hits = self._window(key, config, now)
            if len(hits) >= config.requests:
                return False
            hits.append(now)
            return True

    async def is_allowed(self, key: str, config: RateLimitConfig) -> bool:
        import time

        async with self._lock:
            return len(self._window(key, config, time.monotonic())) < config.requests

    async def remaining(self, key: str, config: RateLimitConfig) -> int:
        import time

        async with self._lock:
            return max(0, config.requests - len(self._window(key, config, time.monotonic())))

    async def reset_after(self, key: str, config: RateLimitConfig) -> int:
        import math
        import time

        async with self._lock:
            now = time.monotonic()
            hits = self._window(key, config, now)
            if not hits:
                return 0
            return max(1, math.ceil(hits[0] + config.window_seconds - now))

    def reset(self) -> None:
        self._hits.clear()


limiter = InMemoryRateLimiter()


async def enforce_rate_limit(key: str, config: RateLimitConfig) -> None:
    """Raise RateLimitError (→ 429 with Retry-After) once `key` exceeds `config`."""
    from app.services.exceptions import RateLimitError

    if not await limiter.hit(key, config):
        raise RateLimitError(retry_after_seconds=await limiter.reset_after(key, config))


def rate_limit(config: RateLimitConfig):
    """FastAPI dependency factory: per-client-IP limit for one route group."""

    async def _dep(request: Request) -> None:
        await enforce_rate_limit(get_rate_limit_key(request, config), config)

    return _dep


# Public guest invite endpoints (view / RSVP) — generous for real guests,
# hostile to token spraying.
PUBLIC_INVITE_RATE_LIMIT = RateLimitConfig(requests=60, window_seconds=60, key_prefix="rl:invite")
# Gate endpoints — a busy gate scans quickly, so per-IP is lenient; repeated
# *failed* verifications are throttled separately per operator scope.
GATE_RATE_LIMIT = RateLimitConfig(requests=180, window_seconds=60, key_prefix="rl:gate")
GATE_FAILURE_LIMIT = RateLimitConfig(requests=30, window_seconds=600, key_prefix="rl:gatefail")


# ── Auth endpoints ────────────────────────────────────────────────────────────

AUTH_ENDPOINT_RATE_LIMIT = RateLimitConfig(
    requests=AUTH_RATE_LIMIT_REQUESTS,
    window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    key_prefix="rl:auth",
)

_auth_limiter = InMemoryRateLimiter()


async def auth_rate_limit(request: Request) -> None:
    """
    FastAPI dependency for sign-in endpoints: at most AUTH_RATE_LIMIT_REQUESTS
    calls per IP per endpoint per window. A brake on password / code guessing
    and on using the API to spam people with codes; the per-account limits
    (OTP sends, failed passwords) cover a slow attack spread over many IPs.

    Counters live in process memory, so with several instances each enforces
    its own share; swap in a shared backend (RateLimiterProtocol) to make the
    limit global.
    """
    from app.services.exceptions import RateLimitError

    key = f"{AUTH_ENDPOINT_RATE_LIMIT.key_prefix}:{request.url.path}:{client_ip(request)}"
    if not await _auth_limiter.hit(key, AUTH_ENDPOINT_RATE_LIMIT):
        raise RateLimitError(
            "Too many attempts. Please wait a minute and try again.",
            retry_after_seconds=AUTH_ENDPOINT_RATE_LIMIT.window_seconds,
        )
