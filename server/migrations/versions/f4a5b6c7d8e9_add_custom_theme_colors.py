"""add custom_theme_colors to celebrations

Revision ID: f4a5b6c7d8e9
Revises: e2f3a4b5c6d7
Create Date: 2026-07-31 00:00:01.000000

Lets a customer supply their own 2-4 color palette for a celebration
instead of picking a preset OccasionTheme — mirrors the existing
bookings.balloon_colors pattern (raw customer-supplied colors, no
catalog row required).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'celebrations',
        sa.Column(
            'custom_theme_colors', postgresql.JSONB(), nullable=True,
            comment="Customer-supplied custom palette (same shape as occasion_themes.colors: "
                    "{primary, secondary, accent, background}), used instead of theme_id when "
                    "the customer picks their own 2-4 colors rather than a preset theme.",
        ),
    )


def downgrade() -> None:
    op.drop_column('celebrations', 'custom_theme_colors')
