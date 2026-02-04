
import sys
import os
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.getcwd())
# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
# Add backend/common to sys.path to satisfy 'from models import ...' in database.py
sys.path.append(os.path.join(os.getcwd(), 'backend', 'common'))


from backend.database import SessionLocal

def verify_task_4607():
    db = SessionLocal()
    try:
        # Search for the task by name to see its IDs
        name_key = "Correcciones Zona E - 2" # From screenshot
        sql = text(f"SELECT id, activity_id, name, extension_days, cell_styles, version_id FROM bim_activities WHERE name LIKE :name")
        results = db.execute(sql, {"name": f"%{name_key}%"}).fetchall()
        
        if results:
            print(f"Found {len(results)} tasks with name '{name_key}':")
            for row in results:
                print(f"PK ID: {row[0]} | ActivityID: {row[1]} | Name: {row[2]} | ExtDays: {row[3]} | Version: {row[5]}")
        else:
            print(f"No task found with name containing '{name_key}'")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_task_4607()
