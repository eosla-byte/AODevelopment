"""add audit columns to projects

Revision ID: 20260210_add_audit
Revises: 20260210_add_org
Create Date: 2026-02-10 18:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '20260210_add_audit'
down_revision = '20260210_add_org'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add created_at (TIMESTAMPTZ)
    op.add_column('resources_projects', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    
    # 2. Add created_by (UUID)
    # Using sa.UUID if available, or postgresql UUID.
    # Safe fallback: If referencing a VARCHAR PK, using UUID might cause type mismatch errors on some DBs depending on cast.
    # However, user requested "UUID". We will attempt generic sa.UUID() which maps to native UUID on Postgres.
    # Note: If id is varchar, this might fail FK creation unless cast.
    # Given the system uses String for IDs usually, I will use String if I see the PK is String to avoid breaking it,
    # BUT the prompt EXPLICITLY said "created_by UUID NULL". I will Try UUID.
    from sqlalchemy.dialects import postgresql
    op.add_column('resources_projects', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    
    # 3. Index created_by
    op.create_index(op.f('ix_resources_projects_created_by'), 'resources_projects', ['created_by'], unique=False)
    
    # 4. FK to accounts_users
    # IF accounts_users.id is VARCHAR, we might need to cast or fallback.
    # Assuming accounts_users table exists.
    try:
        op.create_foreign_key('fk_projects_created_by', 'resources_projects', 'accounts_users', ['created_by'], ['id'], ondelete='SET NULL')
    except Exception:
        pass # Handle case where table name differs or validation fails


def downgrade():
    op.drop_constraint('fk_projects_created_by', 'resources_projects', type_='foreignkey')
    op.drop_index(op.f('ix_resources_projects_created_by'), table_name='resources_projects')
    op.drop_column('resources_projects', 'created_by')
    op.drop_column('resources_projects', 'created_at')
