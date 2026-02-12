"""backfill_accountuser_ids

Revision ID: 20260212_backfill_ids
Revises: 20260211_entitlements
Create Date: 2026-02-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import uuid

# revision identifiers, used by Alembic.
revision = '20260212_backfill_accountuser_ids'
down_revision = '20260211_add_accounts_entitlements_v3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing_tables = insp.get_table_names()

    # Detect User Table Name
    candidates = ["accounts_users", "account_users", "accounts_user", "account_user", "accountuser", "account_users"]
    table_name = None
    for c in candidates:
        if c in existing_tables:
            table_name = c
            break
            
    if not table_name:
         # In some envs, maybe it really doesn't exist? But we are backfilling.
         # If not exists, we can't backfill.
         print("WARNING: User table not found for backfill. Skipping.")
         return

    print(f"Detected User Table: {table_name}")

    # Select users with missing ID
    # We use text() for safety and to avoid model dependencies.
    # We select email to identify the row for update.
    # Note: If ID is primary key and is null, how does that work? 
    # Usually PK cannot be null. But maybe it was created without PK or constraints were loose?
    # Or maybe it's an empty string.
    
    # We will try to fetch all rows where id is null or empty.
    
    select_sql = text(f"SELECT email FROM {table_name} WHERE id IS NULL OR id = ''")
    
    try:
        rows = conn.execute(select_sql).fetchall()
        if not rows:
            print("No users found with missing IDs.")
            return

        print(f"Found {len(rows)} users with missing IDs. Backfilling...")

        for row in rows:
            email = row[0]
            new_id = str(uuid.uuid4())
            
            # Update
            update_sql = text(f"UPDATE {table_name} SET id = :new_id WHERE email = :email")
            conn.execute(update_sql, {"new_id": new_id, "email": email})
            
        print("Backfill complete.")

    except Exception as e:
        print(f"Error during backfill: {e}")
        # We raise to fail the migration if backfill fails, so we know.
        raise e

def downgrade() -> None:
    # No-op: We don't want to remove IDs if we downgrade.
    pass
