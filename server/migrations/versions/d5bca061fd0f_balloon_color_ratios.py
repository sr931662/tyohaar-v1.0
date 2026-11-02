"""balloon_color_ratios on bookings — optional percentage mix of balloon colours

A customer choosing 2-4 balloon colours can now set how much of each they want
(e.g. 30% red, 20% gold, 50% white). Stored as a JSON array aligned with
balloon_colors. NULL (every existing booking) means an even mix, as before.

Revision ID: d5bca061fd0f
Revises: c4e7a19b0d52
Create Date: 2026-11-02 00:00:00.000000
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5bca061fd0f"
down_revision: Union[str, None] = "c4e7a19b0d52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("balloon_color_ratios", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "balloon_color_ratios")
