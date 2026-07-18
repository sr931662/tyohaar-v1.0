"""extend coupons for discount engine

Revision ID: f69692afe4f3
Revises: c8326c837ab8
Create Date: 2026-07-18 15:13:20.054252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f69692afe4f3'
down_revision: Union[str, None] = 'c8326c837ab8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # code becomes nullable — supports automatic (no-code) discounts
    op.alter_column('coupons', 'code', existing_type=sa.String(length=50), nullable=True)

    op.add_column('coupons', sa.Column('is_automatic', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('coupons', sa.Column('public_offer_title', sa.String(length=300), nullable=True))
    op.add_column('coupons', sa.Column('terms_and_conditions', sa.Text(), nullable=True))

    op.add_column('coupons', sa.Column('priority', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('coupons', sa.Column('is_stackable', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('coupons', sa.Column('condition_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.add_column('coupons', sa.Column('admin_status', sa.String(length=20), nullable=False, server_default='draft'))

    op.add_column('coupons', sa.Column('banner_image_url', sa.String(length=2048), nullable=True))
    op.add_column('coupons', sa.Column('theme_color_hex', sa.String(length=7), nullable=True))

    op.add_column('coupons', sa.Column('applicable_occasion_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('coupons', sa.Column('repeat_customers_only', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('coupons', sa.Column('referral_users_only', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('coupons', sa.Column('eligible_customer_group_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('coupons', sa.Column('min_package_value', sa.Numeric(precision=12, scale=2), nullable=True))

    op.add_column('coupons', sa.Column('max_uses_per_day', sa.Integer(), nullable=True))
    op.add_column('coupons', sa.Column('max_uses_per_vendor', sa.Integer(), nullable=True))
    op.add_column('coupons', sa.Column('max_uses_per_package', sa.Integer(), nullable=True))

    op.add_column('bookings', sa.Column('applied_coupon_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('bookings', 'applied_coupon_ids')

    op.drop_column('coupons', 'max_uses_per_package')
    op.drop_column('coupons', 'max_uses_per_vendor')
    op.drop_column('coupons', 'max_uses_per_day')

    op.drop_column('coupons', 'min_package_value')
    op.drop_column('coupons', 'eligible_customer_group_ids')
    op.drop_column('coupons', 'referral_users_only')
    op.drop_column('coupons', 'repeat_customers_only')
    op.drop_column('coupons', 'applicable_occasion_ids')

    op.drop_column('coupons', 'theme_color_hex')
    op.drop_column('coupons', 'banner_image_url')

    op.drop_column('coupons', 'admin_status')

    op.drop_column('coupons', 'condition_rules')
    op.drop_column('coupons', 'is_stackable')
    op.drop_column('coupons', 'priority')

    op.drop_column('coupons', 'terms_and_conditions')
    op.drop_column('coupons', 'public_offer_title')
    op.drop_column('coupons', 'is_automatic')

    op.alter_column('coupons', 'code', existing_type=sa.String(length=50), nullable=False)
