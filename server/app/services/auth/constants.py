from __future__ import annotations

OTP_LENGTH: int = 6
OTP_EXPIRY_SECONDS: int = 300  # 5 minutes
OTP_MAX_ATTEMPTS: int = 3
OTP_RATE_LIMIT_WINDOW_SECONDS: int = 300
OTP_RATE_LIMIT_MAX_REQUESTS: int = 3

ACCESS_TOKEN_EXPIRY_SECONDS: int = 1800   # 30 minutes
REFRESH_TOKEN_EXPIRY_SECONDS: int = 604800  # 7 days

# Window during which presenting an already-rotated refresh token is treated
# as a harmless multi-tab race rather than token theft (see validate_refresh_token).
REFRESH_TOKEN_REUSE_GRACE_SECONDS: int = 10

MAX_ACTIVE_SESSIONS: int = 5

PHONE_REGEX: str = r"^\+91[6-9]\d{9}$"
