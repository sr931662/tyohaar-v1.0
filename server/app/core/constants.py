from __future__ import annotations

# ── Pagination ───────────────────────────────────────────────────────────────
MIN_PAGE_SIZE: int = 1
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
DEFAULT_CURSOR_SIZE: int = 20
MAX_CURSOR_SIZE: int = 100

# ── HTTP Headers ─────────────────────────────────────────────────────────────
REQUEST_ID_HEADER: str = "X-Request-ID"
CORRELATION_ID_HEADER: str = "X-Correlation-ID"
IDEMPOTENCY_KEY_HEADER: str = "Idempotency-Key"
CLIENT_IP_HEADER: str = "X-Forwarded-For"
DEVICE_ID_HEADER: str = "X-Device-ID"
LOCALE_HEADER: str = "Accept-Language"
TIMEZONE_HEADER: str = "X-Timezone"

# ── Auth ─────────────────────────────────────────────────────────────────────
BEARER_PREFIX: str = "Bearer"
JWT_ACCESS_TYPE: str = "access"

# ── Rate Limiting ────────────────────────────────────────────────────────────
DEFAULT_RATE_LIMIT_REQUESTS: int = 60
DEFAULT_RATE_LIMIT_WINDOW_SECONDS: int = 60
AUTH_RATE_LIMIT_REQUESTS: int = 10
AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60

# ── Role groupings ────────────────────────────────────────────────────────────
ADMIN_ROLES: frozenset[str] = frozenset({"admin", "super_admin"})
VENDOR_ROLES: frozenset[str] = frozenset({"vendor"})
CUSTOMER_ROLES: frozenset[str] = frozenset({"customer"})
STAFF_ROLES: frozenset[str] = frozenset({"admin", "super_admin", "support"})
