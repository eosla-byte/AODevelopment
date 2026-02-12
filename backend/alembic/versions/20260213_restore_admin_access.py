"""restore_admin_access

Revision ID: 20260213_restore_admin
Revises: 20260212_backfill_ids
Create Date: 2026-02-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from passlib.context import CryptContext
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '20260213_restore_admin'
down_revision = '20260212_backfill_ids'
branch_labels = None
depends_on = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def upgrade():
    # Define table for data manipulation
    accounts_users = table('accounts_users',
        column('id', sa.String),
        column('email', sa.String),
        column('hashed_password', sa.String),
        column('full_name', sa.String),
        column('role', sa.String),
        column('status', sa.String),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )

    connection = op.get_bind()
    
    admin_email = "superadmin@somosao.com"
    # Ensure correct password is set
    new_hash = get_password_hash("supertata123")
    
    # Check if user exists
    query = sa.select(accounts_users.c.id).where(accounts_users.c.email == admin_email)
    result = connection.execute(query).fetchone()
    
    if result:
        # Update existing user
        print(f"Updating existing superadmin: {admin_email}")
        update_stmt = (
            accounts_users.update()
            .where(accounts_users.c.email == admin_email)
            .values(
                hashed_password=new_hash,
                role='SuperAdmin',
                status='Active',
                updated_at=datetime.utcnow()
            )
        )
        connection.execute(update_stmt)
    else:
        # Insert new user
        print(f"Creating new superadmin: {admin_email}")
        insert_stmt = accounts_users.insert().values(
            id=str(uuid.uuid4()),
            email=admin_email,
            hashed_password=new_hash,
            full_name="Super Admin",
            role='SuperAdmin',
            status='Active',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        connection.execute(insert_stmt)

def downgrade():
    # We do not delete the admin on downgrade to prevent lockout
    pass
