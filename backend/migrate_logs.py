import os
from sqlalchemy import create_engine, text

# DATABASE SETUP
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aodev.db")
engine = create_engine(DATABASE_URL)

def run_migration():
    print(f"Migrating DB: {DATABASE_URL}")
    with engine.connect() as conn:
        try:
            # Check if columns exist
            # Postgres specific check could be complex, so we just Try/Catch ADD COLUMN
            print("Attempting to add 'status' column...")
            conn.execute(text("ALTER TABLE plugin_cloud_commands ADD COLUMN status VARCHAR DEFAULT 'pending'"))
            print("Added 'status'")
        except Exception as e:
            print(f"Skipped status: {e}")

        try:
            print("Attempting to add 'result_json' column...")
            conn.execute(text("ALTER TABLE plugin_cloud_commands ADD COLUMN result_json JSON"))
            print("Added 'result_json'")
        except Exception as e:
            print(f"Skipped result_json: {e}")

        try:
            print("Attempting to add 'error_message' column...")
            conn.execute(text("ALTER TABLE plugin_cloud_commands ADD COLUMN error_message TEXT"))
            print("Added 'error_message'")
        except Exception as e:
            print(f"Skipped error_message: {e}")

        try:
            print("Attempting to add 'updated_at' column...")
            conn.execute(text("ALTER TABLE plugin_cloud_commands ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            print("Added 'updated_at'")
        except Exception as e:
            print(f"Skipped updated_at: {e}")
            
        conn.commit()
    print("Migration Complete.")

if __name__ == "__main__":
    run_migration()
