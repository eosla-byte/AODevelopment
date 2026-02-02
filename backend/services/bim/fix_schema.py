
from services.bim.main import SessionExt, BimActivity
from sqlalchemy import text

def run_migration():
    db = SessionExt()
    try:
        print("Checking/Patching Database Schema...")
        
        # 1. Add style column
        try:
            db.execute(text("ALTER TABLE bim_activities ADD COLUMN IF NOT EXISTS style VARCHAR"))
            print("Added style column")
        except Exception as e:
            print(f"Style column check: {e}")
            
        # 2. Add contractor column
        try:
            db.execute(text("ALTER TABLE bim_activities ADD COLUMN IF NOT EXISTS contractor VARCHAR"))
            print("Added contractor column")
        except Exception as e:
            print(f"Contractor column check: {e}")

        # 3. Add predecessors column
        try:
            db.execute(text("ALTER TABLE bim_activities ADD COLUMN IF NOT EXISTS predecessors VARCHAR"))
            print("Added predecessors column")
        except Exception as e:
            print(f"Predecessors column check: {e}")
            
        # 4. Add comments column
        try:
            # Check DB type? Assuming Postgres (JSONB) or SQLite (JSON/TEXT)
            # Using generic JSON or TEXT if not supported?
            # SQLAlchemy `JSON` maps to JSON in PG.
            # Raw SQL: "ADD COLUMN ... JSON" might fail on SQLite if not enabled? 
            # SQLite supports JSON as TEXT usually.
            # Let's try flexible approach.
            db.execute(text("ALTER TABLE bim_activities ADD COLUMN IF NOT EXISTS comments JSON"))
            print("Added comments column")
        except Exception as e:
            print(f"Comments column check: {e}")
            
        db.commit()
        print("Schema update complete.")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
