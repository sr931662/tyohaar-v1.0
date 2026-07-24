"""add like_count and review aggregate columns to packages and package_items

Revision ID: 92bab569e1f8
Revises: 33716d073051
Create Date: 2026-07-24 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92bab569e1f8'
down_revision: Union[str, None] = '33716d073051'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'packages',
        sa.Column('like_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'package_items',
        sa.Column('average_rating', sa.Numeric(3, 2), nullable=True),
    )
    op.add_column(
        'package_items',
        sa.Column('review_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'package_items',
        sa.Column('like_count', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('package_items', 'like_count')
    op.drop_column('package_items', 'review_count')
    op.drop_column('package_items', 'average_rating')
    op.drop_column('packages', 'like_count')
