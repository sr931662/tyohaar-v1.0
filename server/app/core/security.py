from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer_scheme = HTTPBearer(auto_error=False)


# ── Crypto utilities (consumed by service layer) ─────────────────────────────

def create_access_token(subject: str) -> str:
    """Encode a signed JWT access token with the given subject claim."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> str | None:
    """Decode a JWT and return the subject claim, or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload.get("sub")
    except Exception:
        return None


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    return pwd_context.verify(plain, hashed)


# ── FastAPI dependency helpers ────────────────────────────────────────────────

async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """
    Dependency — extracts the raw Bearer token from the Authorization header.
    Raises HTTP 401 if the header is absent or malformed.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def get_optional_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    """
    Dependency — returns the Bearer token if present, None for unauthenticated
    requests. Never raises — use on public endpoints that accept optional auth.
    """
    return credentials.credentials if credentials is not None else None


def extract_user_id_from_token(token: str) -> str:
    """
    Decode a JWT access token and return the subject (user UUID string).
    Raises HTTP 401 if the token is invalid or expired.
    """
    subject = decode_access_token(token)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject
