
import os
import sys

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from database import SessionLocal
from models import Project

def cleanup():
    # 1. Delete POR1
    print("Deleting POR1...")
    db = SessionLocal()
    p = db.query(Project).filter(Project.id == "POR1").first()
    if p:
        db.delete(p)
        db.commit()
        print("POR1 Deleted.")
    else:
        print("POR1 not found.")
    db.close()
    
    # 2. Delete files
    files = [
        "backend/create_test_proj.py",
        "backend/list_all_proj.py",
        "backend/fix_template_force.py"
    ]
    
    for f in files:
        if os.path.exists(f):
            os.remove(f)
            print(f"Deleted {f}")

if __name__ == "__main__":
    cleanup()
