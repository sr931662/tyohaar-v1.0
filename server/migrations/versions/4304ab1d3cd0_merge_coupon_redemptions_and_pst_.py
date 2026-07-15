"""merge coupon_redemptions and pst branches

Revision ID: 4304ab1d3cd0
Revises: f79355e8d645, 202607151128
Create Date: 2026-07-15 17:51:22.239352

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4304ab1d3cd0'
down_revision: Union[str, None] = ('f79355e8d645', '202607151128')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
