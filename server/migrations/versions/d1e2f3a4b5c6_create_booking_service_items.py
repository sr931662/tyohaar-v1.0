"""create booking_service_items

Revision ID: d1e2f3a4b5c6
Revises: c7d8e9f0a1b2
Create Date: 2026-07-29 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'booking_service_items',
        sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
        sa.Column('booking_id', sa.UUID(), nullable=False),
        sa.Column('package_service_id', sa.UUID(), nullable=True, comment='Source PackageServiceLine this was created from.'),
        sa.Column('vendor_category_id', sa.UUID(), nullable=True, comment='Service type classification (Photography, DJ, etc.)'),
        sa.Column('name', sa.String(length=300), nullable=False, comment='Service name copied from package at booking time (immutable snapshot)'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit', sa.String(length=50), nullable=True, comment="Unit of measure (e.g. 'hours', 'persons')"),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False, comment='Per-unit price charged to the customer'),
        sa.Column('final_price', sa.Numeric(precision=12, scale=2), nullable=False, comment='unit_price × quantity. Computed and stored by service layer.'),
        sa.Column('service_status', sa.Enum('PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'SKIPPED', 'FAILED', name='booking_service_item_status', native_enum=False), nullable=False, server_default='PENDING'),
        sa.Column('is_addon', sa.Boolean(), nullable=False, server_default=sa.false(), comment='True if this service was added as an optional selection'),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default=sa.true(), comment='Copied from PackageServiceLine.is_mandatory at booking time'),
        sa.Column('scheduled_start_at', sa.DateTime(timezone=True), nullable=True, comment='When this specific service is scheduled to start'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('prep_time_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='UTC timestamp when the record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='UTC timestamp of the last ORM-level update'),
        sa.CheckConstraint('quantity >= 1', name=op.f('ck_booking_service_items_ck_booking_service_item_quantity_positive')),
        sa.CheckConstraint('unit_price >= 0', name=op.f('ck_booking_service_items_ck_booking_service_item_unit_price_non_negative')),
        sa.CheckConstraint('final_price >= 0', name=op.f('ck_booking_service_items_ck_booking_service_item_final_price_non_negative')),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_booking_service_items_booking_id_bookings'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['package_service_id'], ['package_services.id'], name=op.f('fk_booking_service_items_package_service_id_package_services'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vendor_category_id'], ['vendor_categories.id'], name=op.f('fk_booking_service_items_vendor_category_id_vendor_categories'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_booking_service_items')),
    )
    op.create_index('ix_booking_service_items_booking_id', 'booking_service_items', ['booking_id'])
    op.create_index('ix_booking_service_items_package_service_id', 'booking_service_items', ['package_service_id'])


def downgrade() -> None:
    op.drop_index('ix_booking_service_items_package_service_id', table_name='booking_service_items')
    op.drop_index('ix_booking_service_items_booking_id', table_name='booking_service_items')
    op.drop_table('booking_service_items')
