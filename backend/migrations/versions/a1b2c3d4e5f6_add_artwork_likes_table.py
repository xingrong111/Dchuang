"""add artwork likes table

Revision ID: a1b2c3d4e5f6
Revises: 1bfd534f0826
Create Date: 2026-09-03

说明（阶段14-B）:
- 新增 artwork_likes 表（用户点赞作品）
- 唯一约束 (user_id, artwork_id): 一人一赞（重复点赞幂等）
- artwork 删除 → likes 级联删除（ondelete CASCADE）
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '1bfd534f0826'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'artwork_likes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('artwork_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['artwork_id'], ['artworks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'artwork_id', name='uq_artwork_likes_user_artwork'),
    )
    op.create_index(op.f('ix_artwork_likes_artwork_id'), 'artwork_likes', ['artwork_id'], unique=False)
    op.create_index(op.f('ix_artwork_likes_created_at'), 'artwork_likes', ['created_at'], unique=False)
    op.create_index(op.f('ix_artwork_likes_user_id'), 'artwork_likes', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_artwork_likes_user_id'), table_name='artwork_likes')
    op.drop_index(op.f('ix_artwork_likes_created_at'), table_name='artwork_likes')
    op.drop_index(op.f('ix_artwork_likes_artwork_id'), table_name='artwork_likes')
    op.drop_table('artwork_likes')
