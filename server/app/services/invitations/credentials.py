"""
Invitation credentials — generation, normalisation, keyed hashing, encryption.

Two secrets exist per guest invitation:

* **Link token** — ``secrets.token_urlsafe(32)`` (256 bits). Lives in the guest's
  personal invite URL (in the fragment, so it never reaches access logs) and
  authorises viewing that one invitation, RSVPing and showing the pass.
* **Entry code** — 8 characters from an unambiguous 31-symbol alphabet
  (~39.6 bits), e.g. ``K7QM-3XPD``. Printed on the pass and encoded in its QR
  as ``TYH1:K7QM3XPD``. It is *not* a bearer credential: it is only accepted by
  an authenticated, celebration-scoped, rate-limited gate operator, and it
  contains no personal data or database identifiers.

Neither is stored in the clear. Lookups go through an HMAC keyed by a server
secret (a database leak alone does not let anyone brute-force codes offline),
and a Fernet ciphertext lets the host re-share the very same link later.
Rotating credentials replaces both, which instantly kills the old link and QR.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

ENTRY_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no I, L, O, 0, 1
ENTRY_CODE_LENGTH = 8
QR_PREFIX = "TYH1:"
GATE_TOKEN_KIND = "gate"
LINK_TOKEN_KIND = "link"
ENTRY_CODE_KIND = "code"


def _base_secret() -> bytes:
    return (settings.INVITATION_TOKEN_KEY or settings.SECRET_KEY).encode()


def _hmac_key() -> bytes:
    return hashlib.sha256(b"tyohaar-invitations-hmac:" + _base_secret()).digest()


def _fernet() -> Fernet:
    key = hashlib.sha256(b"tyohaar-invitations-enc:" + _base_secret()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


# ── Generation ────────────────────────────────────────────────────────────────

def new_link_token() -> str:
    return secrets.token_urlsafe(32)


def new_gate_token() -> str:
    return secrets.token_urlsafe(32)


def new_entry_code() -> str:
    return "".join(secrets.choice(ENTRY_CODE_ALPHABET) for _ in range(ENTRY_CODE_LENGTH))


# ── Normalisation / presentation ──────────────────────────────────────────────

def normalize_entry_code(raw: str | None) -> str | None:
    """
    Accept what a gate operator might type or a scanner might read — mixed
    case, spaces, dashes, the ``TYH1:`` QR prefix — and return the canonical
    8-character code, or None if it cannot possibly be a valid code.
    """
    if not raw:
        return None
    value = raw.strip().upper()
    if value.startswith(QR_PREFIX):
        value = value[len(QR_PREFIX):]
    value = value.replace("-", "").replace(" ", "")
    if len(value) != ENTRY_CODE_LENGTH or any(c not in ENTRY_CODE_ALPHABET for c in value):
        return None
    return value


def format_entry_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


def qr_payload(code: str) -> str:
    """QR content: alphanumeric-mode friendly, versioned, no PII, no IDs."""
    return f"{QR_PREFIX}{code}"


# ── Hashing / encryption ──────────────────────────────────────────────────────

def hash_secret(kind: str, value: str) -> str:
    """Deterministic keyed hash used as the database lookup key."""
    return hmac.new(_hmac_key(), f"{kind}:{value}".encode(), hashlib.sha256).hexdigest()


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str | None) -> str | None:
    """None if absent or undecryptable (e.g. the key was rotated)."""
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def link_lookup(token: str | None) -> str | None:
    """Hash for an incoming link token, rejecting obviously malformed input."""
    if not token or len(token) > 128:
        return None
    return hash_secret(LINK_TOKEN_KIND, token)


def issue_guest_credentials() -> dict[str, str]:
    """Column values for a fresh link token + entry code pair."""
    token = new_link_token()
    code = new_entry_code()
    return {
        "link_token_hash": hash_secret(LINK_TOKEN_KIND, token),
        "link_token_enc": encrypt(token),
        "entry_code_hash": hash_secret(ENTRY_CODE_KIND, code),
        "entry_code_enc": encrypt(code),
    }
