
import os
import sys
from sqlalchemy import create_engine, text

# Setup paths to import common if needed (though we just need DB URL logic)
# Copying DB URL logic from database.py for robustness:

CORE_DB_URL = os.getenv("CORE_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./aodev.db")).strip().replace("postgres://", "postgresql://")
# Services often use EXT_DB_URL or share DATABASE_URL. 
# BIM service uses 'SessionExt', which maps to 'EXT_DB_URL'
# In dev monorepo, they usually all point to same DB or 'aodev.db' sqlite.
EXT_DB_URL = os.getenv("EXT_DB_URL", os.getenv("DATABASE_URL", "sqlite:///./aodev.db")).strip().replace("postgres://", "postgresql://")

print(f"Connecting to DB: {EXT_DB_URL}")

engine = create_engine(EXT_DB_URL)

def run_migration():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Checking schema for 'bim_activities'...")
            
            # 1. Add 'style'
            try:
                conn.execute(text("ALTER TABLE bim_activities ADD COLUMN style VARCHAR"))
                print("Added column: style")
            except Exception as e:
                if "already exists" in str(e):
                    print("Column 'style' already exists.")
                else: 
                    print(f"Error adding 'style': {e}")
                    # Attempt SQLite syntax if different? 
                    # SQLAlchemy usually handles connection, but raw SQL syntax varies.
                    # 'ADD COLUMN' works for both PG and SQLite (mostly).
                    
            # 2. Add 'contractor'
            try:
                conn.execute(text("ALTER TABLE bim_activities ADD COLUMN contractor VARCHAR"))
                print("Added column: contractor")
            except Exception as e:
                if "already exists" in str(e):
                    print("Column 'contractor' already exists.")
                else: print(f"Error adding 'contractor': {e}")
                
            # 3. Add 'predecessors'
            try:
                conn.execute(text("ALTER TABLE bim_activities ADD COLUMN predecessors VARCHAR"))
                print("Added column: predecessors")
            except Exception as e:
                if "already exists" in str(e):
                    print("Column 'predecessors' already exists.")
                else: print(f"Error adding 'predecessors': {e}")

            # 4. Add 'parent_wbs'
            try:
                conn.execute(text("ALTER TABLE bim_activities ADD COLUMN parent_wbs VARCHAR"))
                print("Added column: parent_wbs")
            except Exception as e:
                if "already exists" in str(e):
                    print("Column 'parent_wbs' already exists.")
                else: print(f"Error adding 'parent_wbs': {e}")
                
            # 5. Add 'comments' (JSON)
            # PG: JSON or JSONB. SQLite: JSON (Stored as TEXT usually).
            # We try generic JSON or specific.
            # Using 'JSON' usually maps to PG 'json'.
            try:
                # Determine Dialect
                if 'postgres' in EXT_DB_URL:
                    conn.execute(text("ALTER TABLE bim_activities ADD COLUMN comments JSON DEFAULT '[]'"))
                else:
                    # Sqlite
                    conn.execute(text("ALTER TABLE bim_activities ADD COLUMN comments JSON DEFAULT '[]'"))
                print("Added column: comments")
            except Exception as e:
                if "already exists" in str(e):
                    print("Column 'comments' already exists.")
                else: print(f"Error adding 'comments': {e}")
            
            trans.commit()
            print("Migration completed.")
        except Exception as e:
            trans.rollback()
            print(f"Migration Failed: {e}")
            raise e

if __name__ == "__main__":
    run_migration()
