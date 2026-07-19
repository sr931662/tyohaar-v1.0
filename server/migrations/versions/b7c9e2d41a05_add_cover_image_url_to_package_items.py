"""add cover_image_url to package_items

Revision ID: b7c9e2d41a05
Revises: f69692afe4f3
Create Date: 2026-07-19 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c9e2d41a05'
down_revision: Union[str, None] = 'f69692afe4f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'package_items',
        sa.Column(
            'cover_image_url',
            sa.String(length=500),
            nullable=True,
            comment="Item's cover/thumbnail image, shown on item rows and as the "
                    "first slide of its gallery (mirrors Package.cover_image_url)",
        ),
    )


def downgrade() -> None:
    op.drop_column('package_items', 'cover_image_url')
