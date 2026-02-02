
from services.bim.main import SessionExt, BimActivity
from sqlalchemy import text

def run_migration():
    db = SessionExt()
    try:
        print("Checking/Patching Database Schema...")
        
        # 1. Add style column
        try:
            db.execute(text("ALTER TABLE bim_activities ADD COLUMN style VARCHAR"))
            print("Added style column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "no such column" in str(e).lower(): 
                 # SQLite: duplicate column name
                 print("Style column already exists (or error ignored)")
            else:
                 print(f"Style column check: {e}")
            
        # 2. Add contractor column
        try:
            db.execute(text("ALTER TABLE bim_activities ADD COLUMN contractor VARCHAR"))
            print("Added contractor column")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                 print("Contractor column already exists")
            else:
                 print(f"Contractor column check: {e}")

        # 3. Add predecessors column
        try:
            db.execute(text("ALTER TABLE bim_activities ADD COLUMN predecessors VARCHAR"))
            print("Added predecessors column")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                 print("Predecessors column already exists")
            else:
                 print(f"Predecessors column check: {e}")
            
        # 4. Add comments column
        try:
            # SQLite uses TEXT for JSON usually, or just straight JSON if extension enabled.
            # Safe bet is adding as TEXT or JSON, catching error.
            db.execute(text("ALTER TABLE bim_activities ADD COLUMN comments JSON"))
            print("Added comments column")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                 print("Comments column already exists")
            else:
                 print(f"Comments column check: {e}")
            
        # 5. Add display_order column
        try:
            db.execute(text("ALTER TABLE bim_activities ADD COLUMN display_order INTEGER DEFAULT 0"))
            print("Added display_order column")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                 print("Display_order column already exists")
            else:
                 print(f"Display_order column check: {e}")
            
        db.commit()
        print("Schema update complete.")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
