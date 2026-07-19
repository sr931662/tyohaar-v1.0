"""add preparation_start_at to bookings

Revision ID: c3f8a1b2d4e6
Revises: b7c9e2d41a05
Create Date: 2026-07-19 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f8a1b2d4e6'
down_revision: Union[str, None] = 'b7c9e2d41a05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'bookings',
        sa.Column(
            'preparation_start_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Full date + time at which the vendor will arrive/start "
                    "preparation at the customer's event location (PST)",
        ),
    )


def downgrade() -> None:
    op.drop_column('bookings', 'preparation_start_at')
