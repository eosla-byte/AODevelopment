"""add_slug_to_orgs

Revision ID: 20260213_add_slug_to_orgs
Revises: 20260213_restore_admin
Create Date: 2026-02-13 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '20260213_add_slug_to_orgs'
down_revision = '20260213_restore_admin'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c['name'] for c in inspector.get_columns('accounts_organizations')]
    
    if 'slug' not in columns:
        print("Adding slug column to accounts_organizations")
        op.add_column('accounts_organizations', sa.Column('slug', sa.String(), nullable=True))
        op.create_index(op.f('ix_accounts_organizations_slug'), 'accounts_organizations', ['slug'], unique=True)
        
        # Optional: Backfill slug from name for existing rows if needed
        # For now, allowing nullable=True initially or we'd need a default.
        # But model says unique=True. Nulls allowed in unique in Postgres.
    else:
        print("Column slug already exists.")

def downgrade():
    op.drop_index(op.f('ix_accounts_organizations_slug'), table_name='accounts_organizations')
    op.drop_column('accounts_organizations', 'slug')
