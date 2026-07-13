"""create coupon_redemptions table

Revision ID: f79355e8d645
Revises: c7b770112afd
Create Date: 2026-07-13 21:24:14.566727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f79355e8d645'
down_revision: Union[str, None] = 'c7b770112afd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coupon_redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("coupon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_coupon_redemptions_coupon_id", "coupon_redemptions", ["coupon_id"])
    op.create_index("ix_coupon_redemptions_user_id", "coupon_redemptions", ["user_id"])
    op.create_index(
        "ix_coupon_redemptions_coupon_user", "coupon_redemptions", ["coupon_id", "user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_coupon_redemptions_coupon_user", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_user_id", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_coupon_id", table_name="coupon_redemptions")
    op.drop_table("coupon_redemptions")
