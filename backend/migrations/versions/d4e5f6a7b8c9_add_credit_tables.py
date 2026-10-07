"""add credit ledger tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-03

说明（阶段15-B: 平台积分系统）:
- credit_accounts: 用户积分账户（user_id unique，balance）
- credit_transactions: 积分流水（amount 正=充/退，负=消费；type/reference_id 索引）
- 复合索引 (user_id, created_at)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'credit_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_credit_accounts_user_id'), 'credit_accounts', ['user_id'], unique=True)

    op.create_table(
        'credit_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=30), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_credit_transactions_reference_id'), 'credit_transactions', ['reference_id'], unique=False)
    op.create_index(op.f('ix_credit_transactions_type'), 'credit_transactions', ['type'], unique=False)
    op.create_index(op.f('ix_credit_transactions_user_id'), 'credit_transactions', ['user_id'], unique=False)
    op.create_index('ix_credit_tx_user_created', 'credit_transactions', ['user_id', 'created_at'], unique=False)


def downgrade():
    op.drop_index('ix_credit_tx_user_created', table_name='credit_transactions')
    op.drop_index(op.f('ix_credit_transactions_user_id'), table_name='credit_transactions')
    op.drop_index(op.f('ix_credit_transactions_type'), table_name='credit_transactions')
    op.drop_index(op.f('ix_credit_transactions_reference_id'), table_name='credit_transactions')
    op.drop_table('credit_transactions')
    op.drop_index(op.f('ix_credit_accounts_user_id'), table_name='credit_accounts')
    op.drop_table('credit_accounts')
