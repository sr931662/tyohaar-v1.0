"""Admin service helper utilities."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import Any

from app.core.config import settings


def _legacy_hmac(password: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), password.encode(), hashlib.sha256).hexdigest()


def hash_admin_password(password: str) -> str:
    """
    bcrypt, the same as every other account.

    Admin passwords used to be an unsalted HMAC-SHA256 keyed with SECRET_KEY:
    one fast hash, so anyone holding a copy of the users table and the key
    could test billions of guesses per second. Existing hashes keep verifying
    (see verify_admin_password) and are replaced on the next sign-in.
    """
    from app.core.security import hash_password

    return hash_password(password)


def admin_hash_needs_upgrade(stored_hash: str | None) -> bool:
    """True for a legacy HMAC hash that should be re-saved as bcrypt."""
    return bool(stored_hash) and not stored_hash.startswith("$2")


def verify_admin_password(plain: str, stored_hash: str) -> bool:
    """Check a password against a bcrypt hash, or a legacy HMAC-SHA256 one."""
    if not stored_hash:
        return False
    if stored_hash.startswith("$2"):
        from app.core.security import verify_password

        return verify_password(plain, stored_hash)
    return hmac.compare_digest(_legacy_hmac(plain), stored_hash)


def check_permission(admin_permissions: list[str], required: str) -> bool:
    """Return True if *required* is in the admin's flat permission code list."""
    return required in admin_permissions


def check_permissions_any(admin_permissions: list[str], required: list[str]) -> bool:
    """Return True if the admin holds at least one of the *required* permission codes."""
    return bool(set(required) & set(admin_permissions))


def check_permissions_all(admin_permissions: list[str], required: list[str]) -> bool:
    """Return True only if the admin holds every one of the *required* permission codes."""
    return set(required).issubset(set(admin_permissions))


def format_audit_log_message(
    action: str,
    entity_type: str,
    entity_id: str,
    changes: dict[str, Any],
) -> str:
    """Produce a compact human-readable audit log description string."""
    changes_str = json.dumps(changes, default=str, separators=(",", ":"))
    return f"{action} | {entity_type}:{entity_id} | changes={changes_str}"


def generate_admin_token() -> str:
    """Generate a cryptographically-random 64-char hex admin session token."""
    return secrets.token_hex(32)


def hash_admin_token(token: str) -> str:
    """SHA-256 hash of a raw admin token (used for safe storage)."""
    return hashlib.sha256(token.encode()).hexdigest()
