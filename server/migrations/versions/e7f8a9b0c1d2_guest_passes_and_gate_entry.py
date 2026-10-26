"""guest passes, gate entry logs and delegated gate access

Evolves celebration_guests into a full guest pass:

  * credentials — link_token_hash/enc (replaces the plaintext rsvp_token) and
    entry_code_hash/enc for the QR / manual gate code
  * access rules — pass_status, plus_ones_allowed, arrival window, vehicle,
    revocation fields
  * guest response — rsvp_party_size and guest_note (the guest's RSVP note
    used to overwrite the host's private `notes`)
  * entry — entry_status, checked_out_at, checked_in_party_size, entry_count
  * sharing — last_shared_at/channel, share_count (device-confirmed only)
  * idempotency — client_request_id unique per celebration

Existing invite links keep working: every legacy rsvp_token is hashed and
encrypted into the new columns before the plaintext column is dropped, and
every existing guest is issued an entry code.

Adds actor columns to celebration_guest_history and creates
celebration_gate_accesses and guest_entry_logs.

Enum columns are VARCHARs holding the Python enum member *name*.

Revision ID: e7f8a9b0c1d2
Revises: c1d2e3f4a5b6
Create Date: 2026-10-18 00:00:00.000000
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None

_GUEST_COLUMNS = [
    sa.Column("link_token_hash", sa.String(64), nullable=True),
    sa.Column("link_token_enc", sa.Text(), nullable=True),
    sa.Column("entry_code_hash", sa.String(64), nullable=True),
    sa.Column("entry_code_enc", sa.Text(), nullable=True),
    sa.Column("credentials_rotated_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("client_request_id", sa.String(64), nullable=True),
    sa.Column("pass_status", sa.String(20), nullable=False, server_default="ACTIVE"),
    sa.Column("plus_ones_allowed", sa.SmallInteger(), nullable=False, server_default="0"),
    sa.Column("arrival_window_start", sa.Time(timezone=False), nullable=True),
    sa.Column("arrival_window_end", sa.Time(timezone=False), nullable=True),
    sa.Column("vehicle_number", sa.String(20), nullable=True),
    sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("revoked_reason", sa.String(300), nullable=True),
    sa.Column("rsvp_party_size", sa.SmallInteger(), nullable=True),
    sa.Column("guest_note", sa.Text(), nullable=True),
    sa.Column("entry_status", sa.String(20), nullable=False, server_default="NOT_ARRIVED"),
    sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("checked_in_party_size", sa.SmallInteger(), nullable=True),
    sa.Column("entry_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("last_shared_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("last_shared_channel", sa.String(20), nullable=True),
    sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
]


def _backfill_credentials(conn) -> None:
    from app.services.invitations.credentials import (
        ENTRY_CODE_KIND,
        LINK_TOKEN_KIND,
        encrypt,
        hash_secret,
        new_entry_code,
        new_link_token,
    )

    rows = conn.execute(sa.text("SELECT id, rsvp_token FROM celebration_guests")).fetchall()
    used_codes: set[str] = set()
    for guest_id, legacy_token in rows:
        token = legacy_token or new_link_token()
        code = new_entry_code()
        while code in used_codes:
            code = new_entry_code()
        used_codes.add(code)
        conn.execute(
            sa.text(
                "UPDATE celebration_guests SET link_token_hash = :lh, link_token_enc = :le, "
                "entry_code_hash = :ch, entry_code_enc = :ce WHERE id = :id"
            ),
            {
                "lh": hash_secret(LINK_TOKEN_KIND, token),
                "le": encrypt(token),
                "ch": hash_secret(ENTRY_CODE_KIND, code),
                "ce": encrypt(code),
                "id": guest_id,
            },
        )


def upgrade() -> None:
    conn = op.get_bind()

    for column in _GUEST_COLUMNS:
        op.add_column("celebration_guests", column)

    _backfill_credentials(conn)
    # A legacy checked_in_at (never written by the old code, but possible via
    # direct edits) must not leave the row claiming the guest never arrived.
    conn.execute(sa.text(
        "UPDATE celebration_guests SET entry_status = 'CHECKED_IN', entry_count = 1 "
        "WHERE checked_in_at IS NOT NULL"
    ))

    op.drop_constraint("uq_celebration_guests_rsvp_token", "celebration_guests", type_="unique")
    op.drop_column("celebration_guests", "rsvp_token")

    op.create_unique_constraint(
        "uq_celebration_guests_link_token_hash", "celebration_guests", ["link_token_hash"]
    )
    op.create_unique_constraint(
        "uq_celebration_guests_entry_code_hash", "celebration_guests", ["entry_code_hash"]
    )
    op.create_unique_constraint(
        "uq_celebration_guests_client_request",
        "celebration_guests",
        ["celebration_id", "client_request_id"],
    )
    op.create_index(
        "ix_celebration_guests_entry", "celebration_guests", ["celebration_id", "entry_status"]
    )
    op.create_index(
        "ix_celebration_guests_pass", "celebration_guests", ["celebration_id", "pass_status"]
    )

    op.add_column("celebration_guest_history", sa.Column("actor_type", sa.String(20), nullable=True))
    op.add_column(
        "celebration_guest_history",
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_celebration_guest_history_actor_user_id"),
            nullable=True,
        ),
    )
    op.add_column("celebration_guest_history", sa.Column("actor_label", sa.String(120), nullable=True))
    op.add_column(
        "celebration_guest_history",
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "celebration_gate_accesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "celebration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("celebrations.id", ondelete="CASCADE", name="fk_celebration_gate_accesses_celebration_id"),
            nullable=False,
        ),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_celebration_gate_accesses_created_by_id"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash", name="uq_celebration_gate_accesses_token_hash"),
    )
    op.create_index(
        "ix_celebration_gate_accesses_celebration", "celebration_gate_accesses", ["celebration_id"]
    )

    op.create_table(
        "guest_entry_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "celebration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("celebrations.id", ondelete="CASCADE", name="fk_guest_entry_logs_celebration_id"),
            nullable=False,
        ),
        sa.Column(
            "celebration_guest_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("celebration_guests.id", ondelete="SET NULL", name="fk_guest_entry_logs_guest_id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("result", sa.String(30), nullable=False),
        sa.Column("method", sa.String(10), nullable=False, server_default="manual"),
        sa.Column("party_size", sa.SmallInteger(), nullable=True),
        sa.Column("operator_type", sa.String(20), nullable=False),
        sa.Column(
            "operator_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_guest_entry_logs_operator_user_id"),
            nullable=True,
        ),
        sa.Column(
            "gate_access_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "celebration_gate_accesses.id", ondelete="SET NULL", name="fk_guest_entry_logs_gate_access_id"
            ),
            nullable=True,
        ),
        sa.Column("operator_label", sa.String(120), nullable=True),
        sa.Column("client_scan_id", sa.String(64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_guest_entry_logs_celebration_time", "guest_entry_logs", ["celebration_id", "occurred_at"]
    )
    op.create_index("ix_guest_entry_logs_guest", "guest_entry_logs", ["celebration_guest_id"])
    op.create_index("ix_guest_entry_logs_result", "guest_entry_logs", ["result", "occurred_at"])
    op.create_index(
        "uq_guest_entry_logs_scan",
        "guest_entry_logs",
        ["celebration_guest_id", "action", "client_scan_id"],
        unique=True,
        postgresql_where=sa.text("client_scan_id IS NOT NULL AND celebration_guest_id IS NOT NULL"),
    )


def downgrade() -> None:
    from app.services.invitations.credentials import decrypt

    conn = op.get_bind()
    op.drop_index("uq_guest_entry_logs_scan", table_name="guest_entry_logs")
    op.drop_table("guest_entry_logs")
    op.drop_table("celebration_gate_accesses")

    for column in ("details", "actor_label", "actor_user_id", "actor_type"):
        op.drop_column("celebration_guest_history", column)

    # Restore the plaintext link token so existing invite links survive.
    op.add_column("celebration_guests", sa.Column("rsvp_token", sa.String(64), nullable=True))
    for guest_id, enc in conn.execute(
        sa.text("SELECT id, link_token_enc FROM celebration_guests")
    ).fetchall():
        token = decrypt(enc)
        if token and len(token) <= 64:
            conn.execute(
                sa.text("UPDATE celebration_guests SET rsvp_token = :t WHERE id = :id"),
                {"t": token, "id": guest_id},
            )
    op.create_unique_constraint(
        "uq_celebration_guests_rsvp_token", "celebration_guests", ["rsvp_token"]
    )

    op.drop_index("ix_celebration_guests_pass", table_name="celebration_guests")
    op.drop_index("ix_celebration_guests_entry", table_name="celebration_guests")
    op.drop_constraint("uq_celebration_guests_client_request", "celebration_guests", type_="unique")
    op.drop_constraint("uq_celebration_guests_entry_code_hash", "celebration_guests", type_="unique")
    op.drop_constraint("uq_celebration_guests_link_token_hash", "celebration_guests", type_="unique")
    for column in reversed(_GUEST_COLUMNS):
        op.drop_column("celebration_guests", column.name)
