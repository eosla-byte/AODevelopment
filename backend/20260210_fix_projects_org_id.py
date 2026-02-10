
import sys
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# 1. Setup DB Connection (Standalone)
# Priority: CORE_DB_URL -> DATABASE_URL -> Local SQLite
DB_URL = os.getenv("CORE_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./backend/aodev.db")).strip().replace("postgres://", "postgresql://")

print(f"🔧 [MIGRATION] Connecting to: {DB_URL}")

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

def run_fix():
    print("Beginning Schema Update...")
    db = SessionLocal()
    try:
        # 1. Add Column
        try:
            print("Attempting to add organization_id column...")
            db.execute(text("ALTER TABLE resources_projects ADD COLUMN organization_id VARCHAR"))
            print("✅ Added 'organization_id' column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                 print("ℹ️ 'organization_id' column exists.")
            else:
                 print(f"⚠️ Warning adding column: {e}")

        # 2. Add Index
        try:
            print("Attempting to create index...")
            db.execute(text("CREATE INDEX ix_resources_projects_organization_id ON resources_projects (organization_id)"))
            print("✅ Added Index")
        except Exception as e:
            print(f"ℹ️ Index creation skipped/failed: {e}")

        # 3. Add FK (SQLite checks)
        if "sqlite" not in DB_URL:
            try:
                print("Attempting to add FK constraint...")
                db.execute(text("ALTER TABLE resources_projects ADD CONSTRAINT fk_projects_organization FOREIGN KEY (organization_id) REFERENCES accounts_organizations(id) ON DELETE CASCADE"))
                print("✅ Added Foreign Key Constraint")
            except Exception as e:
                print(f"ℹ️ FK Constraint skipped/failed: {e}")
        else:
            print("ℹ️ SQLite: Skipping ALTER TABLE ADD CONSTRAINT (not supported).")

        db.commit()
        print("🎉 Migration Complete.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Migration Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_fix()
