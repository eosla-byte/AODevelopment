
import sys
import os
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.getcwd())

from backend.database import SessionLocal

def verify_task_4607():
    db = SessionLocal()
    try:
        # Raw SQL to check persistence
        sql = text("SELECT id, name, extension_days, cell_styles FROM bim_activities WHERE id = 4607")
        result = db.execute(sql).fetchone()
        
        if result:
            print(f"Task Found: {result[1]} (ID: {result[0]})")
            print(f"Extension Days: {result[2]}")
            print(f"Cell Styles: {result[3]}")
        else:
            print("Task 4607 NOT FOUND in DB.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_task_4607()
