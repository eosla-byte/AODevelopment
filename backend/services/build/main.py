from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
import os
import datetime
import uuid

# Local Imports
try:
    from common.database import get_build_db, engine_build, Base
    from common.models import BuildProject
except ImportError:
    # Fix path if running directly
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from common.database import get_build_db, engine_build, Base
    from common.models import BuildProject

app = FastAPI(title="AO Build Service")

# Create Tables on Startup (for migration/dev)
@app.on_event("startup")
async def startup_event():
    print("🏗️ [BUILD] Ensuring Database Tables Exist...")
    Base.metadata.create_all(bind=engine_build)

@app.get("/")
def health_check():
    return {"service": "AO Build", "status": "running", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/projects")
def create_build_project(name: str, client: str, db: Session = Depends(get_build_db)):
    proj_id = str(uuid.uuid4())
    new_proj = BuildProject(id=proj_id, name=name, client_name=client)
    db.add(new_proj)
    db.commit()
    db.refresh(new_proj)
    return new_proj

@app.get("/projects")
def list_build_projects(db: Session = Depends(get_build_db)):
    return db.query(BuildProject).all()

@app.get("/version_check")
def version_check():
    return {"version": "v1_build_db_connected"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8006))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
