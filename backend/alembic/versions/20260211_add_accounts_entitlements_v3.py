"""add_accounts_entitlements_v3

Revision ID: 20260211_entitlements
Revises: 20260210_add_project_audit
Create Date: 2026-02-11 17:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260211_add_accounts_entitlements_v3'
down_revision = '20260210_add_project_audit'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check for existence to ensure idempotency
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing_tables = insp.get_table_names()

    # 1. Create accounts_entitlements
    if 'accounts_entitlements' not in existing_tables:
        op.create_table(
            'accounts_entitlements',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('description', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

    # 2. Create accounts_org_entitlements
    if 'accounts_org_entitlements' not in existing_tables:
        op.create_table(
            'accounts_org_entitlements',
            sa.Column('org_id', sa.String(), nullable=False),
            sa.Column('entitlement_key', sa.String(), nullable=False),
            sa.Column('enabled', sa.Boolean(), server_default='true', nullable=True),
            sa.Column('limits_json', sa.JSON(), server_default='{}', nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(['entitlement_key'], ['accounts_entitlements.id'], ),
            sa.ForeignKeyConstraint(['org_id'], ['accounts_organizations.id'], ),
            sa.PrimaryKeyConstraint('org_id', 'entitlement_key')
        )
    
    # 3. Add entitlements_version to accounts_organizations if not exists
    # We use "create_column" with a check, or just try/except block if running?
    # Alembic usually is declarative.
    # Let's check if column exists first.
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [c['name'] for c in insp.get_columns('accounts_organizations')]
    if 'entitlements_version' not in columns:
        op.add_column('accounts_organizations', sa.Column('entitlements_version', sa.Integer(), server_default='1', nullable=True))

    # 4. Seed basic entitlements
    # It's good practice to seed static data in data migrations or separate script, but here is fine.
    op.execute("INSERT INTO accounts_entitlements (id, description) VALUES ('daily', 'AO Daily - Task & Team Management') ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO accounts_entitlements (id, description) VALUES ('bim', 'AO BIM - Scheduling & 4D') ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO accounts_entitlements (id, description) VALUES ('finance', 'AO Finance - Budget & Expenses') ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO accounts_entitlements (id, description) VALUES ('plugin', 'AO Plugin - Revit/Civil3D Connectivity') ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO accounts_entitlements (id, description) VALUES ('build', 'AO Build - Construction Management') ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO accounts_entitlements (id, description) VALUES ('clients', 'AO Clients - Client Portal') ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.drop_table('accounts_org_entitlements')
    op.drop_table('accounts_entitlements')
    op.drop_column('accounts_organizations', 'entitlements_version')
