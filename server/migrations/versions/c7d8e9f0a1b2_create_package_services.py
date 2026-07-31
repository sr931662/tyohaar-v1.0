"""create package_services, package_service_links, package_service_images

Revision ID: c7d8e9f0a1b2
Revises: f9e8d7c6b5a4
Create Date: 2026-07-29 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'f9e8d7c6b5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'package_services',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('package_id', sa.UUID(), nullable=True),
        sa.Column('vendor_id', sa.UUID(), nullable=True),
        sa.Column('is_common', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('category_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('max_quantity', sa.Integer(), nullable=True),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('base_price', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_customizable', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('icon_url', sa.String(500), nullable=True),
        sa.Column('cover_image_url', sa.String(500), nullable=True),
        sa.Column('prep_time_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], name=op.f('fk_package_services_package_id_packages'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], name=op.f('fk_package_services_vendor_id_vendors'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['vendor_categories.id'], name=op.f('fk_package_services_category_id_vendor_categories'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_package_services')),
        sa.CheckConstraint(
            '(is_common AND package_id IS NULL) OR (NOT is_common AND package_id IS NOT NULL)',
            name='ck_package_services_common_xor_package',
        ),
    )
    op.create_index('ix_package_services_package_id', 'package_services', ['package_id'])
    op.create_index('ix_package_services_category_id', 'package_services', ['category_id'])
    op.create_index('ix_package_services_display_order', 'package_services', ['package_id', 'display_order'])
    op.create_index('ix_package_services_vendor_id', 'package_services', ['vendor_id'])

    op.create_table(
        'package_service_links',
        sa.Column('package_id', sa.UUID(), nullable=False),
        sa.Column('package_service_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], name=op.f('fk_package_service_links_package_id_packages'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['package_service_id'], ['package_services.id'], name=op.f('fk_package_service_links_package_service_id_package_services'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('package_id', 'package_service_id', name=op.f('pk_package_service_links')),
    )

    op.create_table(
        'package_service_images',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('service_id', sa.UUID(), nullable=False),
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['service_id'], ['package_services.id'], name=op.f('fk_package_service_images_service_id_package_services'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_package_service_images')),
    )
    op.create_index('ix_package_service_images_service_id', 'package_service_images', ['service_id'])


def downgrade() -> None:
    op.drop_index('ix_package_service_images_service_id', table_name='package_service_images')
    op.drop_table('package_service_images')
    op.drop_table('package_service_links')
    op.drop_index('ix_package_services_vendor_id', table_name='package_services')
    op.drop_index('ix_package_services_display_order', table_name='package_services')
    op.drop_index('ix_package_services_category_id', table_name='package_services')
    op.drop_index('ix_package_services_package_id', table_name='package_services')
    op.drop_table('package_services')
