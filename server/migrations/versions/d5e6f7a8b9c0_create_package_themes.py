"""create package_themes association table

Revision ID: d5e6f7a8b9c0
Revises: c3f8a1b2d4e6
Create Date: 2026-07-22 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c3f8a1b2d4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'package_themes',
        sa.Column('package_id', sa.UUID(), nullable=False),
        sa.Column('theme_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], name=op.f('fk_package_themes_package_id_packages'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['theme_id'], ['occasion_themes.id'], name=op.f('fk_package_themes_theme_id_occasion_themes'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('package_id', 'theme_id', name=op.f('pk_package_themes')),
    )


def downgrade() -> None:
    op.drop_table('package_themes')
