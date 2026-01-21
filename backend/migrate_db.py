
import sqlite3
import os

DB_FILE = "aodev.db"

def migrate():
    if not os.path.exists(DB_FILE):
        print("No DB file found, skipping raw migration (create_all will handle it).")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Create table plugin_project_folders
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plugin_project_folders (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                created_at DATETIME
            )
        """)
        print("Table plugin_project_folders ensured.")
    except Exception as e:
        print(f"Error creating folders table: {e}")

    # 2. Add column folder_id to plugin_cloud_sessions
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(plugin_cloud_sessions)")
        columns = [info[1] for info in cursor.fetchall()]
        if "folder_id" not in columns:
            cursor.execute("ALTER TABLE plugin_cloud_sessions ADD COLUMN folder_id VARCHAR REFERENCES plugin_project_folders(id)")
            print("Column folder_id added to plugin_cloud_sessions.")
        else:
            print("Column folder_id already exists.")
    except Exception as e:
        print(f"Error adding folder_id column: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
