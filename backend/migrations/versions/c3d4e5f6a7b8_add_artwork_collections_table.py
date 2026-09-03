"""add artwork collections table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-03

说明（阶段14-D）:
- 新增 artwork_collections 表（用户收藏作品）
- 唯一约束 (user_id, artwork_id): 一人一收藏（重复收藏幂等）
- artwork 删除 → collections 级联删除（ondelete CASCADE）
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'artwork_collections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('artwork_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['artwork_id'], ['artworks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'artwork_id', name='uq_artwork_collections_user_artwork'),
    )
    op.create_index(op.f('ix_artwork_collections_artwork_id'), 'artwork_collections', ['artwork_id'], unique=False)
    op.create_index(op.f('ix_artwork_collections_created_at'), 'artwork_collections', ['created_at'], unique=False)
    op.create_index(op.f('ix_artwork_collections_user_id'), 'artwork_collections', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_artwork_collections_user_id'), table_name='artwork_collections')
    op.drop_index(op.f('ix_artwork_collections_created_at'), table_name='artwork_collections')
    op.drop_index(op.f('ix_artwork_collections_artwork_id'), table_name='artwork_collections')
    op.drop_table('artwork_collections')
