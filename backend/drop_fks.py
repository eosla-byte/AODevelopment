
import os
import sqlalchemy
from sqlalchemy import create_engine, text

# Get Ops DB URL from environment or default
OPS_DB_URL = os.getenv("OPS_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./aodev.db")).strip().replace("postgres://", "postgresql://")

print(f"🔌 Connecting to Ops DB: {OPS_DB_URL.split('@')[1] if '@' in OPS_DB_URL else 'Local'}")

engine = create_engine(OPS_DB_URL)

def drop_constraint(table, constraint):
    try:
        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            print(f"🔨 Dropping constraint {constraint} on {table}...")
            conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}"))
            print(f"✅ Dropped {constraint}")
    except Exception as e:
        print(f"⚠️ Error dropping {constraint}: {e}")

if __name__ == "__main__":
    # Constraints to drop
    # Based on the error: daily_teams_owner_id_fkey
    # And likely: daily_teams_organization_id_fkey
    # And: daily_projects_organization_id_fkey
    
    constraints = [
        ("daily_teams", "daily_teams_owner_id_fkey"),
        ("daily_teams", "daily_teams_organization_id_fkey"),
        ("daily_projects", "daily_projects_organization_id_fkey")
    ]
    
    for table, cons in constraints:
        drop_constraint(table, cons)
        
    print("🚀 Migration Complete")
