"""create auth tables (user_sessions, refresh_tokens, otp_records) if not exists

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-06-28 00:00:00.000000

These three tables were created outside of Alembic in some environments (e.g.
via create_all during early development).  This migration creates them only when
they are absent so the migration chain is idempotent everywhere.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None

# Max enum name lengths (SQLAlchemy stores enum NAMES, not values, for native_enum=False)
# DeviceType: SMARTWATCH=10, Platform: ANDROID=7, SessionStatus: LOGGED_OUT=10
# TokenRevocationReason: DEVICE_UNREGISTERED=19
# OTPPurpose: TRANSACTION_VERIFICATION=24, OTPDeliveryChannel: WHATSAPP=8, OTPStatus: SUPERSEDED=9


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, "user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column("user_id", pg.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("session_token", sa.String(128), nullable=False, unique=True),
            sa.Column("access_jti", sa.String(128), nullable=True),
            sa.Column("device_id", sa.String(256), nullable=True),
            sa.Column("device_name", sa.String(256), nullable=True),
            sa.Column("device_type", sa.String(50), nullable=True),
            sa.Column("platform", sa.String(50), nullable=True),
            sa.Column("os", sa.String(100), nullable=True),
            sa.Column("os_version", sa.String(50), nullable=True),
            sa.Column("browser", sa.String(100), nullable=True),
            sa.Column("browser_version", sa.String(50), nullable=True),
            sa.Column("app_version", sa.String(50), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("country_code", sa.String(2), nullable=True),
            sa.Column("region", sa.String(100), nullable=True),
            sa.Column("city", sa.String(100), nullable=True),
            sa.Column("timezone", sa.String(100), nullable=True),
            sa.Column("language", sa.String(10), nullable=True),
            sa.Column("login_method", sa.String(50), nullable=False),
            sa.Column("status", sa.String(50), nullable=False),
            sa.Column("login_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("logout_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("remember_me", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true",
                      index=True),
            sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revocation_reason", sa.String(50), nullable=True),
            sa.Column("push_notification_token", sa.Text(), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
        )
        op.create_index("ix_user_session_user_id_active", "user_sessions",
                        ["user_id", "is_active"])
        op.create_index("ix_user_session_session_token", "user_sessions",
                        ["session_token"], unique=True)
        op.create_index("ix_user_session_device_id", "user_sessions", ["device_id"])
        op.create_index("ix_user_session_expires_at", "user_sessions", ["expires_at"])
        op.create_index("ix_user_session_status", "user_sessions", ["status"])

    if not _table_exists(conn, "refresh_tokens"):
        op.create_table(
            "refresh_tokens",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column("jti", sa.String(128), nullable=False, unique=True),
            sa.Column("user_id", pg.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("session_id", pg.UUID(as_uuid=True),
                      sa.ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("family_id", pg.UUID(as_uuid=True), nullable=False),
            sa.Column("parent_jti", sa.String(128), nullable=True),
            sa.Column("token_hash", sa.String(256), nullable=False),
            sa.Column("device_id", sa.String(256), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false",
                      index=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revocation_reason", sa.String(50), nullable=True),
            sa.Column("reuse_detected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reuse_ip_address", sa.String(45), nullable=True),
        )
        op.create_index("ix_refresh_token_jti", "refresh_tokens", ["jti"], unique=True)
        op.create_index("ix_refresh_token_user_id", "refresh_tokens", ["user_id"])
        op.create_index("ix_refresh_token_session_id", "refresh_tokens", ["session_id"])
        op.create_index("ix_refresh_token_family_id", "refresh_tokens", ["family_id"])
        op.create_index("ix_refresh_token_expires_at", "refresh_tokens", ["expires_at"])

    if not _table_exists(conn, "otp_records"):
        op.create_table(
            "otp_records",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column("identifier", sa.String(100), nullable=False),
            sa.Column("channel", sa.String(50), nullable=False),
            sa.Column("purpose", sa.String(50), nullable=False),
            sa.Column("status", sa.String(50), nullable=False),
            sa.Column("otp_hash", sa.String(256), nullable=False),
            sa.Column("attempt_count", sa.SmallInteger(), nullable=False,
                      server_default="0"),
            sa.Column("max_attempts", sa.SmallInteger(), nullable=False,
                      server_default="5"),
            sa.Column("resend_count", sa.SmallInteger(), nullable=False,
                      server_default="0"),
            sa.Column("max_resends", sa.SmallInteger(), nullable=False,
                      server_default="3"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("device_fingerprint", sa.String(256), nullable=True),
            sa.Column("failure_log", pg.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("user_id", pg.UUID(as_uuid=True),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
            sa.CheckConstraint("resend_count >= 0", name="resend_count_non_negative"),
            sa.CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        )
        op.create_index("ix_otp_identifier_purpose_status", "otp_records",
                        ["identifier", "purpose", "status"])
        op.create_index("ix_otp_expires_at", "otp_records", ["expires_at"])
        op.create_index("ix_otp_user_id", "otp_records", ["user_id"])


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "otp_records"):
        op.drop_table("otp_records")
    if _table_exists(conn, "refresh_tokens"):
        op.drop_table("refresh_tokens")
    if _table_exists(conn, "user_sessions"):
        op.drop_table("user_sessions")
