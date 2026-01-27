
from fastapi import FastAPI, Request, Depends, HTTPException, status, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
import uvicorn
import os
import sys
import uuid
import datetime

# Path Setup to allow importing 'backend.common'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_ROOT not in sys.path:
    # Append root for common modules
    sys.path.append(BACKEND_ROOT)

# PRIORITIZE LOCAL IMPORTS: Insert current dir at the start of sys.path
# This ensures that 'import routers' picks up the local './routers' folder 
# instead of the global '/app/routers' package found in BACKEND_ROOT
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
elif sys.path[0] != BASE_DIR:
    # Ensure it's first if it was elsewhere
    sys.path.remove(BASE_DIR)
    sys.path.insert(0, BASE_DIR)

from common.database import get_db, SessionExt 
# Note: For this service, get_db should ideally point to SessionExt or we explicitely use SessionExt
from common.auth_utils import decode_access_token
from common.models import BimUser, BimOrganization, BimProject, BimScheduleVersion, BimActivity
try:
    from .schedule_parser import parse_schedule
except ImportError:
    from schedule_parser import parse_schedule

try:
    from .routers import auth
except ImportError:
    # Fallback to direct import, relying on sys.path[0] == BASE_DIR
    import routers.auth as auth

app = FastAPI(title="AO PlanSystem (BIM Portal)")

# Mount Static if needed (Shared assets or dedicated?)
# For now, we can use CDN for tailwind, or mount shared if we want logos
# app.mount("/static", StaticFiles(directory=os.path.join(BACKEND_ROOT, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Include Routers
app.include_router(auth.router)

# Dependencies
def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        scheme, _, param = token.partition(" ")
        payload = decode_access_token(param)
        if not payload: return None
        return payload # Returns dict {"sub": email, "role": role, "org": org_id}
    except:
        return None

@app.get("/", response_class=HTMLResponse)
async def root(user = Depends(get_current_user)):
    if user:
        return RedirectResponse("/dashboard")
    return RedirectResponse("/auth/login")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/auth/login")
        
    # Fetch Org Name details?
    db = SessionExt()
    user_db = db.query(BimUser).filter(BimUser.email == user["sub"]).first()
    org_name = "Organización"
    if user_db and user_db.organization:
        org_name = user_db.organization.name
    db.close()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user_name": user.get("sub"), # Or Full Name if in token/db
        "user_initials": user.get("sub")[:2].upper(),
        "org_name": org_name
    })

@app.get("/projects", response_class=HTMLResponse)
async def projects_list(request: Request, user = Depends(get_current_user)):
    if not user: return RedirectResponse("/auth/login")
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user_name": user.get("sub"), "user_initials": user.get("sub")[:2], "org_name": "TBD"
    })

@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def view_project_gantt(request: Request, project_id: str, user = Depends(get_current_user)):
    if not user: return RedirectResponse("/auth/login")
    
    # 1. Fetch Project & Latest Version
    db = SessionExt()
    project = db.query(BimProject).filter(BimProject.id == project_id).first()
    
    # Mock Data if no project found (or create on fly for demo?)
    if not project:
         # Create Dummy for demo
         project = BimProject(id=project_id, name="Proyecto Demo Torre A", organization_id="1")
    
    # Fetch Activities from DB
    # For now, we return empty list or mock list
    tasks = []
    
    # Transform for Frappe Gantt
    # Format: {id: "Task 1", name: "Redesign website", start: "2016-12-28", end: "2016-12-31", progress: 20, dependencies: "Task 2, Task 3"}
    tasks_json = [
        {
            "id": "A100",
            "name": "Cimentación Profunda",
            "start": "2024-02-01",
            "end": "2024-02-15",
            "progress": 100,
            "dependencies": ""
        },
        {
            "id": "A110",
            "name": "Estructura Nivel 1",
            "start": "2024-02-16",
            "end": "2024-03-01",
            "progress": 45,
            "dependencies": "A100"
        },
         {
            "id": "A120",
            "name": "Estructura Nivel 2",
            "start": "2024-03-02",
            "end": "2024-03-15",
            "progress": 0,
            "dependencies": "A110"
        }
    ]
    import json
    tasks_str = json.dumps(tasks_json)

    db.close()

    return templates.TemplateResponse("project_gantt.html", {
        "request": request,
        "project": project,
        "tasks": tasks_json,
        "tasks_json": tasks_str
    })

@app.post("/projects/{project_id}/schedule/upload")
async def upload_schedule(project_id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    if not user: return RedirectResponse("/auth/login")
    
    # 1. Read File
    content = await file.read()
    
    try:
        # 2. Parse (Simulated)
        schedule_data = parse_schedule(content, file.filename)
        
        # 3. Save Version (Basic Implementation)
        db = SessionExt()
        
        new_version = BimScheduleVersion(
            id=str(uuid.uuid4()),
            project_id=project_id,
            version_name=f"Import {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            source_filename=file.filename,
            source_type=file.filename.split('.')[-1].upper(),
            imported_by=user['sub'] # Ideally ID
        )
        db.add(new_version)
        db.commit()
        
        # 4. Save Activities (Mock Loop)
        # for act in schedule_data['activities']: ...
        
        db.close()
        
        return {"status": "ok", "message": "Schedule imported successfully"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8004))
    print(f"Starting BIM Service on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)