"""Addresses, product favorites, verified-order reviews and shipment references."""
from alembic import op
import sqlalchemy as sa
revision = 'ad1020260003'
down_revision = 'ac1020260002'
branch_labels = depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('carrier', sa.String(80)))
    op.add_column('orders', sa.Column('tracking_number', sa.String(100)))
    op.create_table('shipping_addresses', sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
                    sa.Column('receiver', sa.String(80), nullable=False), sa.Column('phone', sa.String(30), nullable=False),
                    sa.Column('address', sa.String(500), nullable=False), sa.Column('is_default', sa.Boolean(), nullable=False))
    op.create_index('ix_shipping_addresses_user_id', 'shipping_addresses', ['user_id'])
    op.create_table('product_favorites', sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
                    sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), primary_key=True),
                    sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_table('product_reviews', sa.Column('id', sa.Integer(), primary_key=True),
                    sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
                    sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
                    sa.Column('order_id', sa.String(64), sa.ForeignKey('orders.id'), nullable=False),
                    sa.Column('rating', sa.Integer(), nullable=False), sa.Column('content', sa.String(1000), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False), sa.UniqueConstraint('order_id', 'product_id'))
    op.create_index('ix_product_reviews_product_id', 'product_reviews', ['product_id'])


def downgrade():
    op.drop_table('product_reviews')
    op.drop_table('product_favorites')
    op.drop_table('shipping_addresses')
    op.drop_column('orders', 'tracking_number')
    op.drop_column('orders', 'carrier')
