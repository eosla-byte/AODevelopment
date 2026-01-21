import sqlite3
import os

DB_PATH = "aodev.db"

def migrate():
    print(f"Migrating {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Add permissions to resources_users
    try:
        print("Adding permissions column to resources_users...")
        cursor.execute("ALTER TABLE resources_users ADD COLUMN permissions TEXT DEFAULT '{}'")
        print("Success.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'permissions' already exists.")
        else:
            print(f"Error: {e}")

    # 2. Add plugin_version to plugin_sessions
    try:
        print("Adding plugin_version column to plugin_sessions...")
        cursor.execute("ALTER TABLE plugin_sessions ADD COLUMN plugin_version TEXT DEFAULT '1.0.0'")
        print("Success.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'plugin_version' already exists.")
        else:
            print(f"Error: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
