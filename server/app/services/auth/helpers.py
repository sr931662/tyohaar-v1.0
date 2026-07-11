"""
Pure helper functions for the auth service — no I/O, no database access.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from jose.exceptions import ExpiredSignatureError as JWTExpiredError
from jose.exceptions import JWTError

from app.services.auth.exceptions import InvalidRefreshTokenError


def generate_otp() -> str:
    """Return a 6-digit numeric OTP string."""
    return str(secrets.randbelow(1_000_000)).zfill(6)


def otp_email_html(otp: str, purpose_label: str, expire_minutes: int) -> str:
    """Minimal inline-styled HTML body for an OTP email (no external assets)."""
    return f"""\
<div style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px;">
  <h2 style="color: #2A2018; margin: 0 0 16px;">Tyohaar</h2>
  <p style="color: #2A2018; font-size: 15px; line-height: 1.6;">
    Use the code below to {purpose_label}. It expires in {expire_minutes} minutes.
  </p>
  <div style="background: #F6F1E8; border-radius: 12px; padding: 20px; text-align: center; margin: 24px 0;">
    <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #C8791E;">{otp}</span>
  </div>
  <p style="color: #6B5D50; font-size: 13px; line-height: 1.6;">
    If you didn't request this code, you can safely ignore this email.
  </p>
</div>"""


def hash_otp(phone: str, otp: str, secret_key: str) -> str:
    """HMAC-SHA256(key=secret_key, msg=phone+otp). Returns hex digest."""
    msg = (phone + otp).encode("utf-8")
    return hmac.new(secret_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def verify_otp_hash(phone: str, otp: str, stored_hash: str, secret_key: str) -> bool:
    """Re-derive the HMAC and compare in constant time."""
    expected = hash_otp(phone, otp, secret_key)
    return hmac.compare_digest(expected, stored_hash)


def hash_token(token: str) -> str:
    """SHA-256 of a raw token string. Returns hex digest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token(length: int = 32) -> str:
    """Return a cryptographically random hex string of the given byte length."""
    return secrets.token_hex(length)


def create_access_token_payload(
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    expires_in: int,
) -> dict:
    """
    Build a JWT payload dict.

    Args:
        user_id:    UUID of the authenticated user (becomes the ``sub`` claim).
        session_id: UUID of the current session.
        expires_in: Token TTL in seconds.

    Returns:
        Payload dict ready for encode_jwt().
    """
    now = datetime.now(tz=timezone.utc)
    jti = str(uuid.uuid4())
    return {
        "sub": str(user_id),
        "session_id": str(session_id),
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }


def encode_jwt(payload: dict, secret: str, algorithm: str = "HS256") -> str:
    """Encode a payload dict as a signed JWT."""
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_jwt(token: str, secret: str, algorithm: str = "HS256") -> dict:
    """
    Decode and validate a JWT.

    Raises:
        InvalidRefreshTokenError: if the token is expired, has a bad signature,
            or is otherwise invalid.
    """
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except JWTExpiredError as exc:
        raise InvalidRefreshTokenError("Token has expired.") from exc
    except JWTError as exc:
        raise InvalidRefreshTokenError(f"Token is invalid: {exc}") from exc
