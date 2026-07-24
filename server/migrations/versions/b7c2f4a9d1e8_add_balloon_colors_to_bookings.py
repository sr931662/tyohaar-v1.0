"""add balloon colour fields to bookings

Revision ID: b7c2f4a9d1e8
Revises: d5e6f7a8b9c0
Create Date: 2026-07-23 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7c2f4a9d1e8'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'bookings',
        sa.Column(
            'balloon_color_mode',
            sa.Enum('SINGLE', 'DUAL', name='balloon_color_mode', native_enum=False),
            nullable=True,
            comment="Customer's chosen balloon décor style: a single accent colour or a two-colour combination.",
        ),
    )
    op.add_column(
        'bookings',
        sa.Column(
            'balloon_colors',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Hex codes of the chosen balloon colour(s) — 1 item for SINGLE mode, 2 for DUAL.",
        ),
    )


def downgrade() -> None:
    op.drop_column('bookings', 'balloon_colors')
    op.drop_column('bookings', 'balloon_color_mode')
