"""add allow_balloon_theme to occasions

Revision ID: a4b5c6d7e8f9
Revises: f4a5b6c7d8e9
Create Date: 2026-08-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'occasions',
        sa.Column(
            'allow_balloon_theme',
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment=(
                "Whether packages under this occasion may offer the balloon "
                "colour/theme customization step. Admin-disabled for religious "
                "and cultural occasions (e.g. Mehndi, Haldi, Diwali) where a "
                "balloon décor setup would look out of place."
            ),
        ),
    )
    op.alter_column('occasions', 'allow_balloon_theme', server_default=None)


def downgrade() -> None:
    op.drop_column('occasions', 'allow_balloon_theme')
