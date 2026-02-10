import sys
import os

# Add path to backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from services.build.common.database import get_build_db, engine_build, Base
from services.build.common.models import BuildProject
import uuid

def verify_build_db():
    print("🏗️ Verifying Build Service DB...")
    
    # 1. Create Tables
    print("   Creating tables...")
    Base.metadata.create_all(bind=engine_build)
    
    # 2. Insert Data
    db = next(get_build_db())
    proj_id = str(uuid.uuid4())
    print(f"   Inserting Project {proj_id}...")
    
    new_proj = BuildProject(id=proj_id, name="Test Build Project", client_name="Test Client")
    db.add(new_proj)
    db.commit()
    
    # 3. Query Data
    print("   Querying data...")
    fetched = db.query(BuildProject).filter_by(id=proj_id).first()
    
    if fetched:
        print(f"✅ Success! Found project: {fetched.name} ({fetched.id})")
    else:
        print("❌ Failed to retrieve project.")
        
    db.close()

if __name__ == "__main__":
    verify_build_db()
