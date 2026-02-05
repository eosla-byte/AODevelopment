
import sys
import os

# Add backend directory to sys.path to allow imports from common
sys.path.append(os.getcwd())

from common.database import SessionOps
from sqlalchemy import text

def run_migration():
    print("Migrating resources_projects table in Ops DB...")
    db = SessionOps()
    try:
        # 1. organization_id
        try:
            db.execute(text("ALTER TABLE resources_projects ADD COLUMN organization_id VARCHAR"))
            print("Added organization_id column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("organization_id already exists")
            else:
                print(f"Error adding organization_id: {e}")

        # 2. project_cost
        try:
            db.execute(text("ALTER TABLE resources_projects ADD COLUMN project_cost FLOAT DEFAULT 0.0"))
            print("Added project_cost column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("project_cost already exists")
            else:
                print(f"Error adding project_cost: {e}")

        # 3. sq_meters
        try:
            db.execute(text("ALTER TABLE resources_projects ADD COLUMN sq_meters FLOAT DEFAULT 0.0"))
            print("Added sq_meters column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("sq_meters already exists")
            else:
                print(f"Error adding sq_meters: {e}")

        # 4. ratio
        try:
            db.execute(text("ALTER TABLE resources_projects ADD COLUMN ratio FLOAT DEFAULT 0.0"))
            print("Added ratio column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("ratio already exists")
            else:
                print(f"Error adding ratio: {e}")

        # 5. estimated_time
        try:
            db.execute(text("ALTER TABLE resources_projects ADD COLUMN estimated_time VARCHAR"))
            print("Added estimated_time column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("estimated_time already exists")
            else:
                print(f"Error adding estimated_time: {e}")

        db.commit()
        print("Migration complete.")
    except Exception as e:
        db.rollback()
        print(f"Migration failed completely: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
