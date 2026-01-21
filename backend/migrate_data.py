import os
import json
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

ROOT_PATH = os.path.dirname(os.path.abspath(__file__)) # database.py location
PROJECTS_DIR = os.path.join(ROOT_PATH, "Local_DB", "Projects")
HR_DIR = os.path.join(ROOT_PATH, "Local_DB", "Collaborators")

def migrate_projects(db: Session):
    print(f"Scanning Projects in {PROJECTS_DIR}...")
    if not os.path.exists(PROJECTS_DIR):
        print("Projects directory not found.")
        return

    count = 0
    subdirs = [os.path.join(PROJECTS_DIR, d) for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))]
    
    for p_dir in subdirs:
        folder_name = os.path.basename(p_dir)
        p_id = str(hash(folder_name))
        p_name = folder_name
        
        parts = folder_name.split(" - ", 1)
        if len(parts) == 2:
            p_id = parts[0]
            p_name = parts[1]
            
        # Check if exists
        existing = db.query(models.Project).filter(models.Project.id == p_id).first()
        if existing:
            print(f"Skipping {p_name} (Already exists)")
            continue
            
        print(f"Migrating {p_name}...")
        
        # Read Meta
        meta_path = os.path.join(p_dir, "meta.json")
        data = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Error reading meta for {folder_name}: {e}")
                
        # Create Object
        proj = models.Project(
            id=p_id,
            name=p_name,
            client=data.get("client", ""),
            status=data.get("status", "Activo"),
            nit=data.get("nit", ""),
            legal_name=data.get("legal_name", ""),
            po_number=data.get("po_number", ""),
            amount=float(data.get("amount", 0.0)),
            paid_amount=float(data.get("paid_amount", 0.0)),
            emoji=data.get("emoji", "📁"),
            category=data.get("category", "Residencial"),
            square_meters=float(data.get("square_meters", 0.0)),
            start_date=data.get("start_date", ""),
            duration_months=float(data.get("duration_months", 0)),
            additional_time_months=float(data.get("additional_time_months", 0)),
            archived=data.get("archived", False),
            # JSON Fields
            acc_config=data.get("acc_config", {}),
            partners_config=data.get("partners_config", {}),
            files_meta=data.get("files_meta", {}),
            reminders=data.get("reminders", []),
            projected_profit_margin=float(data.get("projected_profit_margin", 0.0)),
            real_profit_margin=float(data.get("real_profit_margin", 0.0))
        )
        
        try:
            db.add(proj)
            db.commit()
            count += 1
            print(f"Migrated {p_name}")
        except Exception as e:
            db.rollback()
            print(f"FAILED to migrate {p_name}: {e}")
            # Continue to next
            continue

def migrate_collaborators(db: Session):
    print(f"Scanning Collaborators in {HR_DIR}...")
    if not os.path.exists(HR_DIR):
        print("Collaborators directory not found.")
        return

    count = 0
    subdirs = [os.path.join(HR_DIR, d) for d in os.listdir(HR_DIR) if os.path.isdir(os.path.join(HR_DIR, d))]
    
    for c_dir in subdirs:
        folder_name = os.path.basename(c_dir)
        c_id = str(hash(folder_name))
        c_name = folder_name
        
        parts = folder_name.split(" - ", 1)
        if len(parts) == 2:
            c_id = parts[0]
            c_name = parts[1]
            
        existing = db.query(models.Collaborator).filter(models.Collaborator.id == c_id).first()
        if existing:
            continue
            
        print(f"Migrating {c_name}...")
        
        meta_path = os.path.join(c_dir, "meta.json")
        data = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    data = json.load(f)
            except: pass
            
        collab = models.Collaborator(
            id=c_id,
            name=c_name,
            email=data.get("email", ""),
            role=data.get("role", "Collaborator"),
            base_salary=float(data.get("base_salary", 0.0)),
            bonus_incentive=float(data.get("bonus_incentive", 0.0)),
            salary=float(data.get("salary", 0.0)),
            birthday=data.get("birthday", ""),
            start_date=data.get("start_date", ""),
            accumulated_liability=float(data.get("accumulated_liability", 0.0)),
            profile_picture=data.get("profile_picture", ""),
            status=data.get("status", "Activo"),
            archived=data.get("archived", False),
            adjustments=data.get("adjustments", [])
        )
        try:
            db.add(collab)
            db.commit()
            count += 1
            print(f"Migrated {c_name}")
        except Exception as e:
            db.rollback()
            print(f"FAILED to migrate {c_name}: {e}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        migrate_projects(db)
        migrate_collaborators(db)
    finally:
        db.close()
