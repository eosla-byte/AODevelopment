
from backend.services.daily.common import database, models
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid

def patch_data():
    db_core = database.SessionCore()
    db_ops = database.SessionOps()
    
    try:
        # 1. Get First Available Organization
        org = db_core.query(models.Organization).first()
        if not org:
            print("⚠️ No organizations found! Creating a DEFAULT organization for local testing.")
            org_id = str(uuid.uuid4())
            org = models.Organization(id=org_id, name="AO Development (Local)", status="Active")
            db_core.add(org)
            db_core.commit()
            print(f"✅ Created Default Organization: {org.name} ({org.id})")
        else:
            print(f"✅ Using Existing Organization: {org.name} ({org.id})")

        # 2. Patch Daily Projects
        projects = db_ops.query(models.DailyProject).filter(models.DailyProject.organization_id == None).all()
        print(f"🔍 Found {len(projects)} projects without Organization ID.")
        
        count = 0
        for p in projects:
            p.organization_id = org.id
            count += 1
            print(f"   -> Patching Project '{p.name}' with OrgID {org.id}")
            
        if count > 0:
            db_ops.commit()
            print(f"✅ Successfully patched {count} projects.")
        else:
            print("✨ No projects needed patching.")

    except Exception as e:
        print(f"❌ Error patching data: {e}")
        db_ops.rollback()
    finally:
        db_core.close()
        db_ops.close()

if __name__ == "__main__":
    patch_data()
