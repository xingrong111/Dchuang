"""Persist password reset challenges across WSGI processes."""
from alembic import op
import sqlalchemy as sa
revision = 'ac1020260002'
down_revision = 'ab1020260001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('password_reset_codes',
        sa.Column('email', sa.String(120), primary_key=True),
        sa.Column('digest', sa.String(64), nullable=False),
        sa.Column('nonce', sa.String(32), nullable=False),
        sa.Column('expires', sa.Double(), nullable=False),
        sa.Column('sent_at', sa.Double(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False))


def downgrade():
    op.drop_table('password_reset_codes')
