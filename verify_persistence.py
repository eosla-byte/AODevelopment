
import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Replicate generic DB connection logic
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aodev.db").strip().replace("postgres://", "postgresql://")
# Hardcoded to what I see in previous logs or context if possible, otherwise use the env var logic
# The user's railway logs show "100.64.0.2" etc, implying external DB possibly, or just internal routing.
# But locally I am on windows. The user said "The user's OS version is windows".
# I should try to connect to the LOCAL sqlite first if it exists, roughly at "backend/aodev.db" or "./aodev.db" relative to root?
# backend/database.py says: sqlite:///./aodev.db
# IF running from root a:\AO_DEVELOPMENT\AODevelopment, then ./aodev.db would be in root.
# IF running from backend, it would be in backend.
# Let's check where the file is.

def get_db_url():
    # Check for sqlite file specific locations
    if os.path.exists("backend/aodev.db"):
        return "sqlite:///backend/aodev.db"
    if os.path.exists("aodev.db"):
        return "sqlite:///aodev.db"
    if os.path.exists("backend/services/bim/bim.db"): # maybe checking BIM service specific?
         return "sqlite:///backend/services/bim/bim.db"
    
    # Fallback to env or default
    return os.getenv("DATABASE_URL", "sqlite:///./aodev.db").replace("postgres://", "postgresql://")

url = get_db_url()
print(f"Connecting to: {url}")

engine = create_engine(url)
SessionLocal = sessionmaker(bind=engine)

def check_task(task_id):
    db = SessionLocal()
    try:
        # Check raw SQL
        sql = text("SELECT id, name, extension_days, cell_styles FROM bim_activities WHERE id = :id")
        result = db.execute(sql, {"id": task_id}).fetchone()
        
        if result:
            print(f"FOUND TASK: {task_id}")
            print(f"Name: {result[1]}")
            print(f"Extension Days: {result[2]}")
            print(f"Cell Styles: {result[3]}")
        else:
            print(f"Task {task_id} NOT FOUND in DB.")
            
    except Exception as e:
        print(f"Error querying DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Check task 4615 (from logs)
    check_task(4615)
