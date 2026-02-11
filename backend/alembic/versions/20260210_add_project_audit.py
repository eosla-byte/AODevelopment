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
    # 1. Add created_at
    op.add_column('resources_projects', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True))
    
    # 2. Add created_by
    op.add_column('resources_projects', sa.Column('created_by', sa.String(), nullable=True))
    
    # 3. Index created_by
    op.create_index(op.f('ix_resources_projects_created_by'), 'resources_projects', ['created_by'], unique=False)
    
    # 4. FK to accounts_users
    # Note: user id is string/uuid
    op.create_foreign_key('fk_projects_created_by', 'resources_projects', 'accounts_users', ['created_by'], ['id'])


def downgrade():
    op.drop_constraint('fk_projects_created_by', 'resources_projects', type_='foreignkey')
    op.drop_index(op.f('ix_resources_projects_created_by'), table_name='resources_projects')
    op.drop_column('resources_projects', 'created_by')
    op.drop_column('resources_projects', 'created_at')
