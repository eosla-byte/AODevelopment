
import os
import sys

# Setup Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Back up to root "backend"
BACKEND_ROOT = BASE_DIR
if BACKEND_ROOT not in sys.path:
    sys.path.append(BACKEND_ROOT)

from common.database import SessionExt, engine_ext
from sqlalchemy import text

def run_migration():
    print("Starting Migration for Advanced Gantt...")
    db = SessionExt()
    try:
        # Check if we are using SQLite
        if 'sqlite' in str(engine_ext.url):
             print("Detected SQLite.")
             # SQLite doesn't support IF NOT EXISTS in ALTER TABLE usually, so we try and catch
             
             # 1. Add contractor
             try:
                 print("Adding column 'contractor'...")
                 db.execute(text("ALTER TABLE bim_activities ADD COLUMN contractor VARCHAR"))
                 print("Added 'contractor'.")
             except Exception as e:
                 if "duplicate column" in str(e) or "no such table" in str(e):
                     print(f"Skipping 'contractor' (exists or table missing): {e}")
                 else:
                     print(f"Error adding 'contractor': {e}")

             # 2. Add predecessors
             try:
                 print("Adding column 'predecessors'...")
                 db.execute(text("ALTER TABLE bim_activities ADD COLUMN predecessors VARCHAR"))
                 print("Added 'predecessors'.")
             except Exception as e:
                 if "duplicate column" in str(e):
                     print(f"Skipping 'predecessors' (exists): {e}")
                 else:
                     print(f"Error adding 'predecessors': {e}")
            
             # 3. Add style
             try:
                 print("Adding column 'style'...")
                 db.execute(text("ALTER TABLE bim_activities ADD COLUMN style VARCHAR"))
                 print("Added 'style'.")
             except Exception as e:
                 if "duplicate column" in str(e):
                     print(f"Skipping 'style' (exists): {e}")
                 else:
                     print(f"Error adding 'style': {e}")
                     
             db.commit()
        else:
            print("Not SQLite? Implementation requires manual check for PG/Others.")
            
    except Exception as global_e:
        print(f"Critical Migration Error: {global_e}")
    finally:
        db.close()
        print("Migration Finished.")

if __name__ == "__main__":
    run_migration()
