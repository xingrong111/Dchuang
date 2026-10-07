"""Allow curated public artworks without creating a user account."""
from alembic import op
import sqlalchemy as sa
revision = 'ae1020260004'
down_revision = 'ad1020260003'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('artworks') as batch:
        batch.alter_column('user_id', existing_type=sa.Integer(), nullable=True)

def downgrade():
    # Do not erase showcase works implicitly during a downgrade.
    connection = op.get_bind()
    if connection.execute(sa.text('SELECT COUNT(*) FROM artworks WHERE user_id IS NULL')).scalar():
        raise RuntimeError('Remove or assign platform artworks before downgrading')
    with op.batch_alter_table('artworks') as batch:
        batch.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
