"""add ai provider config table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-03

说明（阶段16-B）:
- ai_providers: AI Provider 运营配置（启用开关 + 成本配置）
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('provider_type', sa.String(length=10), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('cost_config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index(op.f('ix_ai_providers_name'), 'ai_providers', ['name'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_ai_providers_name'), table_name='ai_providers')
    op.drop_table('ai_providers')
