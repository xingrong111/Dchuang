"""商品、购物车、订单"""
from alembic import op
import sqlalchemy as sa
revision = 'ab1020260001'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('products', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(120), nullable=False), sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(30), nullable=False), sa.Column('price_cents', sa.Integer(), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=False), sa.Column('image', sa.String(500)),
        sa.Column('specs', sa.JSON()), sa.Column('active', sa.Boolean(), nullable=False))
    op.create_table('cart_items', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False), sa.UniqueConstraint('user_id', 'product_id'))
    op.create_table('orders', sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('request_key', sa.String(64), nullable=False), sa.Column('items', sa.JSON(), nullable=False),
        sa.Column('total_cents', sa.Integer(), nullable=False), sa.Column('receiver', sa.String(80), nullable=False),
        sa.Column('phone', sa.String(30), nullable=False), sa.Column('address', sa.String(500), nullable=False),
        sa.Column('note', sa.String(500)), sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime()), sa.UniqueConstraint('user_id', 'request_key'))
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])


def downgrade():
    op.drop_table('orders')
    op.drop_table('cart_items')
    op.drop_table('products')
