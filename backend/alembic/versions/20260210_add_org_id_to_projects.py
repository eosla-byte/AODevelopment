"""add organization_id to projects

Revision ID: 20260210_add_org
Revises: 
Create Date: 2026-02-10 17:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260210_add_org'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add Column
    op.add_column('resources_projects', sa.Column('organization_id', sa.String(), nullable=True))
    
    # 2. Create Index
    op.create_index(op.f('ix_resources_projects_organization_id'), 'resources_projects', ['organization_id'], unique=False)
    
    # 3. Create ForeignKey
    op.create_foreign_key('fk_projects_organization', 'resources_projects', 'accounts_organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    
    # 4. Update existing nullable? (Optional manual step usually)
    # op.alter_column('resources_projects', 'organization_id', nullable=False)


def downgrade():
    op.drop_constraint('fk_projects_organization', 'resources_projects', type_='foreignkey')
    op.drop_index(op.f('ix_resources_projects_organization_id'), table_name='resources_projects')
    op.drop_column('resources_projects', 'organization_id')
