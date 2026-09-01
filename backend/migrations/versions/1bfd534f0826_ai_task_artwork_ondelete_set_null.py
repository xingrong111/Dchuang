"""ai task artwork ondelete set null

Revision ID: 1bfd534f0826
Revises: 0f6b0abfa81e
Create Date: 2026-09-01 22:06:27.109904

说明（人工修正）:
- Alembic 自动生成版本使用 drop_constraint(None)，在 SQLite batch 模式下无法定位约束。
- 本版本使用显式约束名 fk_ai_tasks_artwork_id，batch 模式重建表时
  新表按 ondelete='SET NULL' 创建外键（drop 在 batch 重建中为 no-op）。
- 效果: Artwork 删除后 AITask 保留，artwork_id 置 NULL（保留 AI 任务历史）。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1bfd534f0826'
down_revision = '0f6b0abfa81e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ai_tasks', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ai_tasks_artwork_id', type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_ai_tasks_artwork_id', 'artworks', ['artwork_id'], ['id'],
            ondelete='SET NULL'
        )


def downgrade():
    with op.batch_alter_table('ai_tasks', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ai_tasks_artwork_id', type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_ai_tasks_artwork_id', 'artworks', ['artwork_id'], ['id']
        )
