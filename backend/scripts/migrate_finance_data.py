import os
import sys
import argparse
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.dialects.postgresql import insert
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
TABLES_TO_MIGRATE = [
    "bim_projects",
    "resources_collaborators",
    "resources_users", 
    "resources_expense_columns", 
    "resources_expense_cards",
    "resources_quotations",
    "resources_quotation_templates",
    "resources_timeline_events"
]

def get_engine(url):
    if not url:
        return None
    return create_engine(url)

def migrate_table(source_conn, target_conn, table_name, clean=False):
    logger.info(f"migrating table: {table_name}")
    
    # Reflect tables
    source_meta = MetaData()
    target_meta = MetaData()
    
    try:
        source_table = Table(table_name, source_meta, autoload_with=source_conn)
    except Exception as e:
        logger.warning(f"Source table {table_name} not found or error: {e}")
        return

    try:
        target_table = Table(table_name, target_meta, autoload_with=target_conn)
    except Exception as e:
        logger.warning(f"Target table {table_name} not found (please run migrations first): {e}")
        return

    # Clean Target if requested
    if clean:
        logger.info(f"Cleaning target table {table_name}...")
        target_conn.execute(target_table.delete())
        target_conn.commit()

    # Read Source Data
    query = select(source_table)
    result = source_conn.execute(query)
    rows = result.fetchall()
    
    if not rows:
        logger.info(f"No data in {table_name}")
        return

    logger.info(f"Found {len(rows)} rows in {table_name}")
    
    # Insert Data
    # We use column names to map, avoiding index issues if schema slightly differs but compatible
    keys = source_table.columns.keys()
    
    data_to_insert = []
    for row in rows:
        row_dict = {k: v for k, v in zip(keys, row)}
        data_to_insert.append(row_dict)

    # Batch Insert
    batch_size = 1000
    for i in range(0, len(data_to_insert), batch_size):
        batch = data_to_insert[i:i+batch_size]
        stmt = insert(target_table).values(batch)
        
        # On Conflict Do Nothing (Idempotent)
        # Assuming PK exists
        pk = [key.name for key in target_table.primary_key]
        if pk:
             stmt = stmt.on_conflict_do_nothing(index_elements=pk)
        
        target_conn.execute(stmt)
        target_conn.commit()
        
    logger.info(f"Migrated {len(data_to_insert)} rows for {table_name}")

def main():
    parser = argparse.ArgumentParser(description="Migrate Finance Data from Source to Target DB")
    parser.add_argument("--source", help="Source Database URL", required=False)
    parser.add_argument("--target", help="Target Database URL", required=False)
    parser.add_argument("--clean", action="store_true", help="Truncate target tables before migration")
    
    args = parser.parse_args()
    
    source_urL = args.source or os.getenv("CORE_DB_URL") or os.getenv("DATABASE_URL")
    target_url = args.target or os.getenv("OPS_DB_URL")
    
    if not source_urL:
        logger.error("Source URL is missing. Set CORE_DB_URL or pass --source")
        return
    if not target_url:
        logger.error("Target URL is missing. Set OPS_DB_URL or pass --target")
        return
        
    logger.info(f"Source: {source_urL.split('@')[-1]}") # Hide credential
    logger.info(f"Target: {target_url.split('@')[-1]}")
    
    try:
        source_engine = get_engine(source_urL)
        target_engine = get_engine(target_url)
        
        with source_engine.connect() as source_conn, target_engine.connect() as target_conn:
             for table in TABLES_TO_MIGRATE:
                 migrate_table(source_conn, target_conn, table, args.clean)
                 
        logger.info("Migration Complete ✅")
        
    except Exception as e:
        logger.error(f"Migration Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
