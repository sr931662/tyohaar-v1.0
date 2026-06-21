"""
RefreshToken — JWT refresh token persistence with rotation and reuse detection.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import TokenRevocationReason
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Persistent record for every issued refresh token, supporting rotation
    and automatic reuse detection.

    Token Rotation:
    - When a client exchanges a refresh token for a new access token, the
      current refresh token is consumed (is_used = True, used_at = now()).
    - A new refresh token is issued and linked to the consumed one via parent_jti.
    - The client must store only the newest token; presenting a used token is a
      security signal, not a normal operation.

    Token Families:
    - Every token issued from the same login event shares a family_id UUID.
    - family_id is the primary handle for revoking an entire token chain.
    - The chain is: token_A (root) → token_B (parent_jti=A) → token_C (parent_jti=B).

    Reuse Detection:
    - If is_used = True when a token arrives, an attacker likely stole the
      previous token before it was rotated.
    - Handler must:
        1. Set reuse_detected_at on the presented token.
        2. Immediately revoke ALL tokens sharing family_id with reason REUSE_DETECTED.
        3. Revoke the associated UserSession.
        4. Notify the legitimate user via push/email.

    Token Hash:
    - The raw refresh token string is NEVER stored.
    - Only token_hash (SHA-256 of the raw token) is persisted.
    - Verification: recompute hash of presented token, compare to stored hash.

    Reference:
    - Auth0 — Refresh Token Rotation:
      https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation
    """

    __tablename__ = "refresh_tokens"

    __table_args__ = (
        Index("ix_refresh_token_jti", "jti", unique=True),
        Index("ix_refresh_token_user_id", "user_id"),
        Index("ix_refresh_token_session_id", "session_id"),
        # Family-wide revocation is the most performance-critical query
        Index("ix_refresh_token_family_id", "family_id"),
        # Cleanup: find all expired tokens without scanning is_revoked
        Index("ix_refresh_token_expires_at", "expires_at"),
    )

    # ── JWT Identity ──────────────────────────────────────────────────────────

    jti: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        comment=(
            "JWT ID — the 'jti' claim embedded in the issued refresh JWT. "
            "This is the stable lookup key; used to find this record without "
            "decoding the full token."
        ),
    )

    # ── Ownership & Binding ───────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="The user this token grants access on behalf of",
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment=(
            "The session this token is bound to. "
            "Revoking the session must also revoke all its refresh tokens."
        ),
    )

    # ── Rotation Chain ────────────────────────────────────────────────────────

    family_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        comment=(
            "Shared identifier for all tokens derived from one login event. "
            "The root token sets this; all rotated successors inherit it. "
            "Revoking a family instantly invalidates all tokens in the chain."
        ),
    )

    parent_jti: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment=(
            "jti of the token that was consumed to produce this token. "
            "NULL for the first (root) token in a family. "
            "Builds an auditable rotation chain: A → B → C."
        ),
    )

    # ── Stored Credential ─────────────────────────────────────────────────────

    token_hash: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment=(
            "SHA-256(raw_refresh_token). "
            "The raw token is never persisted. "
            "Verification: hash the presented token and compare."
        ),
    )

    # ── Device Binding ────────────────────────────────────────────────────────

    device_id: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        comment=(
            "Device identifier at issuance time. "
            "A device_id mismatch at presentation is a high-confidence security signal."
        ),
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP at issuance time (IPv4 or IPv6)",
    )

    # ── Lifecycle Timestamps ──────────────────────────────────────────────────

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when this token was created and returned to the client",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment=(
            "Absolute expiry. The token is invalid after this regardless of "
            "rotation or revocation state. Typical value: 30–90 days."
        ),
    )

    # ── Rotation State ────────────────────────────────────────────────────────

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True once this token has been exchanged for a new one via rotation. "
            "A used token MUST be rejected on any subsequent presentation."
        ),
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the legitimate rotation exchange that consumed this token",
    )

    # ── Revocation ────────────────────────────────────────────────────────────

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revocation_reason: Mapped[TokenRevocationReason | None] = mapped_column(
        SAEnum(TokenRevocationReason, name="token_revocation_reason", native_enum=False),
        nullable=True,
    )

    # ── Reuse Detection ───────────────────────────────────────────────────────

    reuse_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Set when this already-consumed token is presented again. "
            "Presence of this value triggers immediate family-wide revocation "
            "and a security notification to the legitimate account owner."
        ),
    )

    reuse_ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address of the client that attempted the token reuse",
    )

    # ── Computed Properties ───────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """True only if this token can be presented for a rotation exchange."""
        return (
            not self.is_used
            and not self.is_revoked
            and not self.is_expired
        )

    def __repr__(self) -> str:
        return (
            f"<RefreshToken jti={self.jti!r} user_id={self.user_id} "
            f"is_used={self.is_used} is_revoked={self.is_revoked}>"
        )
