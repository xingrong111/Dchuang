"""add artwork comments table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-03

说明（阶段14-C）:
- 新增 artwork_comments 表（作品评论）
- artwork 删除 → comments 级联删除（ondelete CASCADE）
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'artwork_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('artwork_id', sa.String(length=64), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['artwork_id'], ['artworks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_artwork_comments_artwork_id'), 'artwork_comments', ['artwork_id'], unique=False)
    op.create_index(op.f('ix_artwork_comments_created_at'), 'artwork_comments', ['created_at'], unique=False)
    op.create_index(op.f('ix_artwork_comments_user_id'), 'artwork_comments', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_artwork_comments_user_id'), table_name='artwork_comments')
    op.drop_index(op.f('ix_artwork_comments_created_at'), table_name='artwork_comments')
    op.drop_index(op.f('ix_artwork_comments_artwork_id'), table_name='artwork_comments')
    op.drop_table('artwork_comments')
