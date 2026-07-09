"""add rsvp_token and invitation_opened_at to celebration_guests

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-09 00:00:00.000000
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
        ),
        {"t": table_name, "c": column_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "celebration_guests", "rsvp_token"):
        op.add_column(
            'celebration_guests',
            sa.Column('rsvp_token', sa.String(64), nullable=True),
        )
        op.create_unique_constraint(
            'uq_celebration_guests_rsvp_token', 'celebration_guests', ['rsvp_token']
        )

    if not _column_exists(conn, "celebration_guests", "invitation_opened_at"):
        op.add_column(
            'celebration_guests',
            sa.Column('invitation_opened_at', sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "celebration_guests", "invitation_opened_at"):
        op.drop_column('celebration_guests', 'invitation_opened_at')
    if _column_exists(conn, "celebration_guests", "rsvp_token"):
        op.drop_constraint('uq_celebration_guests_rsvp_token', 'celebration_guests', type_='unique')
        op.drop_column('celebration_guests', 'rsvp_token')
