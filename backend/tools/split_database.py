
import os
import sys
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.schema import CreateTable
from sqlalchemy.exc import SQLAlchemyError

# Ensure we can import from backend
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from backend.common.models import Base

# DB CONFIGURATION (From Env Vars or arguments)
# Users must export these before running
SOURCE_DB_URL = os.getenv("SOURCE_DB_URL") 
CORE_DB_URL = os.getenv("CORE_DB_URL")       # db-core
OPS_DB_URL = os.getenv("OPS_DB_URL")         # db-operations
PLUGIN_DB_URL = os.getenv("PLUGIN_DB_URL")   # db-plugin
EXT_DB_URL = os.getenv("EXT_DB_URL")         # db-external

# TABLE MAPPING
TABLE_MAP = {
    "db-core": [
        "resources_users"
    ],
    "db-operations": [
        "resources_projects", 
        "resources_timeline_events", 
        "resources_collaborators",
        "resources_expense_columns",
        "resources_expense_cards",
        "resources_quotations",
        "resources_quotation_templates"
    ],
    "db-plugin": [
        "plugin_licenses",
        "plugin_logs",
        "plugin_sessions",
        "plugin_activities",
        "plugin_versions",
        "plugin_project_folders",
        "plugin_cloud_sessions",
        "plugin_cloud_commands",
        "plugin_routines",
        "plugin_sheet_templates",
        "plugin_sheet_sessions"
    ],
    "db-external": [
        "web_contact_submissions"
    ]
}

def migrate():
    if not all([SOURCE_DB_URL, CORE_DB_URL, OPS_DB_URL, PLUGIN_DB_URL, EXT_DB_URL]):
        print("ERROR: Missing one or more Environment Variables:")
        print("SOURCE_DB_URL, CORE_DB_URL, OPS_DB_URL, PLUGIN_DB_URL, EXT_DB_URL")
        return

    print("--- Starting Migration ---")
    
    # 1. Connect to Source
    src_engine = create_engine(SOURCE_DB_URL)
    src_meta = MetaData()
    src_meta.reflect(bind=src_engine)
    
    # 2. Prepare Targets
    targets = {
        "db-core": create_engine(CORE_DB_URL),
        "db-operations": create_engine(OPS_DB_URL),
        "db-plugin": create_engine(PLUGIN_DB_URL),
        "db-external": create_engine(EXT_DB_URL)
    }
    
    # 3. Process
    for target_name, engine in targets.items():
        print(f"\nProcessing {target_name}...")
        tables_to_move = TABLE_MAP.get(target_name, [])
        
        with engine.begin() as conn:
            for table_name in tables_to_move:
                if table_name not in src_meta.tables:
                    print(f"  [WARN] Table {table_name} not found in source. Skipping.")
                    continue
                
                src_table = src_meta.tables[table_name]
                print(f"  Migrating {table_name}...")
                
                # A. Create Table if not exists
                # We use the SQLAlchemy model definition from 'Base' if possible, or reflected?
                # Reflected is safer for data structure fidelity if models changed.
                # However, CreateTable(src_table) works well.
                try:
                    src_table.create(bind=conn, checkfirst=True)
                except Exception as e:
                    print(f"  [Error Creating {table_name}] {e}")
                
                # B. Copy Data
                # Select all from source
                data = []
                with src_engine.connect() as src_conn:
                    result = src_conn.execute(src_table.select())
                    # Format as list of dicts
                    keys = result.keys()
                    data = [dict(zip(keys, row)) for row in result.fetchall()]
                
                if data:
                    print(f"    - Moving {len(data)} rows...")
                    # Insert chunked if necessary, but for this size mostly fine.
                    # We need to handle potential PK conflicts if re-running (upsert not standard in vanilla SQLA core easily cross-db)
                    # For migration: Delete all first? Or just try insert?
                    # Let's clean target first to ensure clean state (Migration Mode)
                    conn.execute(src_table.delete())
                    conn.execute(src_table.insert(), data)
                    print("    - Done.")
                else:
                    print("    - No data.")

    print("\n--- Migration Complete ---")

if __name__ == "__main__":
    migrate()
