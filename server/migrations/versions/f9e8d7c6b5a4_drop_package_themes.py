"""drop package_themes association table

Revision ID: f9e8d7c6b5a4
Revises: 77471ae03007
Create Date: 2026-07-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9e8d7c6b5a4'
down_revision: Union[str, None] = '77471ae03007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Every theme in the catalog is now available on every customizable
    # package — the vendor-curated subset this table implemented is removed.
    op.drop_table('package_themes')


def downgrade() -> None:
    op.create_table(
        'package_themes',
        sa.Column('package_id', sa.UUID(), nullable=False),
        sa.Column('theme_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], name=op.f('fk_package_themes_package_id_packages'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['theme_id'], ['occasion_themes.id'], name=op.f('fk_package_themes_theme_id_occasion_themes'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('package_id', 'theme_id', name=op.f('pk_package_themes')),
    )
