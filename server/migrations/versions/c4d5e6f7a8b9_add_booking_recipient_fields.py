"""add recipient_name and recipient_phone to bookings

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-07-11 00:00:00.000000

The Booking model has always declared these two columns, but no migration
ever created them — every booking creation attempt has been failing with
"column bookings.recipient_name does not exist" (production schema drift,
discovered while live-testing the plan flow's item_ids wiring).
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
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

    if not _column_exists(conn, "bookings", "recipient_name"):
        op.add_column(
            'bookings',
            sa.Column('recipient_name', sa.String(200), nullable=True),
        )

    if not _column_exists(conn, "bookings", "recipient_phone"):
        op.add_column(
            'bookings',
            sa.Column('recipient_phone', sa.String(20), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "bookings", "recipient_phone"):
        op.drop_column('bookings', 'recipient_phone')
    if _column_exists(conn, "bookings", "recipient_name"):
        op.drop_column('bookings', 'recipient_name')
