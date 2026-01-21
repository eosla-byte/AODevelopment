import sqlite3
import os

DB_FILE = "aodev.db"

def migrate():
    if not os.path.exists(DB_FILE):
        print("Database file not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(resources_projects)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "estimation_data" not in columns:
        print("Adding estimation_data column...")
        try:
            # SQLite doesn't strictly have JSON type, but we can store it as TEXT/JSON
            cursor.execute("ALTER TABLE resources_projects ADD COLUMN estimation_data JSON")
            conn.commit()
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("Column estimation_data already exists.")
        
    conn.close()

if __name__ == "__main__":
    migrate()
