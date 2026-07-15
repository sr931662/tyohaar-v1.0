"""add pst to bookings

Revision ID: 202607151128
Revises: c7b770112afd
Create Date: 2026-07-15 11:28:50.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202607151128'
down_revision: Union[str, None] = 'c7b770112afd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bookings', sa.Column('preparation_start_time', sa.Time(), nullable=True, comment='Preparation Starting Time [PST] provided by the vendor'))


def downgrade() -> None:
    op.drop_column('bookings', 'preparation_start_time')
