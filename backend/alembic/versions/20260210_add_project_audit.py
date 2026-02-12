"""add audit columns to projects

Revision ID: 20260210_add_audit
Revises: 20260210_add_org
Create Date: 2026-02-10 18:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '20260210_add_project_audit'
down_revision = '20260210_add_org_id_to_projects'
branch_labels = None
depends_on = None


from sqlalchemy import inspect

def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("resources_projects")}
    indexes = {i["name"] for i in inspector.get_indexes("resources_projects")}
    constraints = {c["name"] for c in inspector.get_foreign_keys("resources_projects")}

    # 1. Add created_at (TIMESTAMPTZ)
    if 'created_at' not in cols:
        op.add_column('resources_projects', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    
    # 2. Add created_by (UUID)
    if 'created_by' not in cols:
        from sqlalchemy.dialects import postgresql
        op.add_column('resources_projects', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    
    # 3. Index created_by
    if 'ix_resources_projects_created_by' not in indexes:
        op.create_index(op.f('ix_resources_projects_created_by'), 'resources_projects', ['created_by'], unique=False)
    
    # 4. FK to accounts_users
    if 'fk_projects_created_by' not in constraints:
        try:
            op.create_foreign_key('fk_projects_created_by', 'resources_projects', 'accounts_users', ['created_by'], ['id'], ondelete='SET NULL')
        except Exception:
            pass # Handle case where table name differs or validation fails


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("resources_projects")}
    indexes = {i["name"] for i in inspector.get_indexes("resources_projects")}
    constraints = {c["name"] for c in inspector.get_foreign_keys("resources_projects")}

    if 'fk_projects_created_by' in constraints:
        op.drop_constraint('fk_projects_created_by', 'resources_projects', type_='foreignkey')
        
    if 'ix_resources_projects_created_by' in indexes:
        op.drop_index(op.f('ix_resources_projects_created_by'), table_name='resources_projects')
        
    if 'created_by' in cols:
        op.drop_column('resources_projects', 'created_by')
        
    if 'created_at' in cols:
        op.drop_column('resources_projects', 'created_at')
