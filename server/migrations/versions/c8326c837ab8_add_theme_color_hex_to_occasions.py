"""add theme_color_hex to occasions

Revision ID: c8326c837ab8
Revises: 4304ab1d3cd0
Create Date: 2026-07-18 14:23:30.513842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8326c837ab8'
down_revision: Union[str, None] = '4304ab1d3cd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'occasions',
        sa.Column('theme_color_hex', sa.String(length=7), nullable=True, comment="Brand/accent color for this occasion's cards, e.g. '#C8A96E'"),
    )


def downgrade() -> None:
    op.drop_column('occasions', 'theme_color_hex')
