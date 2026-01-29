
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
from common.auth_utils import decode_access_token, require_org_access
from common.models import BimUser, BimOrganization, BimProject, BimScheduleVersion, BimActivity
try:
    from .schedule_parser import parse_schedule
except ImportError:
    from schedule_parser import parse_schedule

try:
    from routers import auth as auth
except ImportError:
    # Fallback to direct import, relying on sys.path[0] == BASE_DIR
    import routers.auth as auth

app = FastAPI(title="AO PlanSystem (BIM Portal)")

@app.get("/api/context-debug")
def debug_context(
    ctx: dict = Depends(require_org_access("bim"))
):
    """
    Debug Endpoint to verify Multi-Tenant Isolation.
    Requires header X-Organization-ID and active service permission.
    """
    return {
        "status": "authorized", 
        "context": ctx,
        "message": f"Welcome to BIM Workspace for Org {ctx['org_id']}"
    }

# Mount Static if needed (Shared assets or dedicated?)
from common.models import Organization, OrganizationUser, ServicePermission
from common.auth_utils import get_current_user

@app.get("/api/me/organizations")
def get_my_organizations(
    db: SessionExt = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of organizations the user belongs to THAT HAVE BIM ENABLED.
    """
    user_id = current_user.get("id")
    
    # 1. Get Memberships
    memberships = db.query(OrganizationUser).filter(OrganizationUser.user_id == user_id).all()
    org_ids = [m.organization_id for m in memberships]
    
    if not org_ids:
        return []

    # 2. Filter by Service Permission 'bim' = Active
    valid_perms = db.query(ServicePermission).filter(
        ServicePermission.organization_id.in_(org_ids),
        ServicePermission.service_slug == "bim",
        ServicePermission.is_active == True
    ).all()
    
    valid_org_ids = [p.organization_id for p in valid_perms]
    
    # 3. Fetch Organization Details
    # Also check USER specific permission per org? 
    # Logic in require_org_access: "if not is_org_admin and not user_perms.get(service_slug)"
    # We should replicate that logic to NOT show orgs where user is restricted.
    
    final_orgs = []
    
    valid_orgs_db = db.query(Organization).filter(Organization.id.in_(valid_org_ids)).all()
    org_map = {o.id: o for o in valid_orgs_db}
    
    for m in memberships:
        if m.organization_id in valid_org_ids:
            # Check User Perms
            if m.role != "Admin":
                perms = m.permissions or {}
                if not perms.get("bim"):
                    continue # Skip this org, user doesn't have access
            
            org = org_map.get(m.organization_id)
            if org:
                final_orgs.append({
                    "id": org.id,
                    "name": org.name,
                    "role": m.role
                })
                
    return final_orgs
# For now, we can use CDN for tailwind, or mount shared if we want logos
# app.mount("/static", StaticFiles(directory=os.path.join(BACKEND_ROOT, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Include Routers
app.include_router(auth.router)

# Dependencies
# Dependencies
# Use imported get_current_user from common.auth_utils

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Root Entry Point.
    - If not logged in -> Login.
    - If logged in -> Show Organization Selector.
    """
    # Note: get_current_user raises 401 if missing, but for HTML routes we often want Redirect.
    # But since we use Depends(get_current_user) which raises HTTPException, 
    # we might need a "soft" dependency or handle exception globally.
    # For now, if get_current_user fails, it shows JSON error. 
    # BETTER: Use a try/except helper or allow optional.
    # Let's rely on the frontend redirecting if 401?
    # Actually, common.auth_utils.get_current_user logic raises 401.
    # To prevent JSON 401 on homepage, we should accept it might fail?
    # But Depends() execution happens before function body.
    # I'll let it raise 401 and let browser show raw error? No user experience bad.
    # I will modify this to use a "get_optional_user" logic? 
    # Or just assume if they hit / they might be redirected by JS in org_selector.
    
    # Wait, if I use the template org_selector, it does a fetch("/api/me/organizations").
    # If THAT returns 401, the JS redirects to login.
    # So I can just return the HTML without enforcing user check here?
    # Yes, serve the shell, let the shell authenticate.
    return templates.TemplateResponse("org_selector.html", {"request": request})

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    user = Depends(get_current_user),
    org_id: str = None # Optional
):
    """
    Workspace Dashboard.
    If org_id missing, auto-select first valid org.
    """
    db = SessionCore()
    try:
         user_id = user['id']
         
         # 1. Handle Missing Org ID (Auto-Select)
         if not org_id:
             # Fetch valid memberships
             memberships = db.query(OrganizationUser).filter(
                 OrganizationUser.user_id == user_id
             ).all()
             
             for m in memberships:
                 # Check Service Perm for this Org
                 op = db.query(ServicePermission).filter(
                    ServicePermission.organization_id == m.organization_id,
                    ServicePermission.service_slug == "bim",
                    ServicePermission.is_active == True
                 ).first()
                 
                 # Also check User Perm if not Admin (Strict check)
                 if op:
                     if m.role == "Admin" or (m.permissions and m.permissions.get("bim")):
                         return RedirectResponse(f"/dashboard?org_id={m.organization_id}")
             
             # If no valid orgs found
             return HTMLResponse("<h1>No accessible BIM Organizations found. Contact your Admin.</h1>", status_code=403)

         # 2. Validate Specific Org Access
         membership = db.query(OrganizationUser).filter(
             OrganizationUser.organization_id == org_id,
             OrganizationUser.user_id == user_id
         ).first()
         
         if not membership:
             # Redirect to selector if invalid
             return RedirectResponse("/")
             
         # Check Service Perm
         # (Assuming if they got here via selector, they have it, but verify)
         org_perm = db.query(ServicePermission).filter(
            ServicePermission.organization_id == org_id,
            ServicePermission.service_slug == "bim",
            ServicePermission.is_active == True
         ).first()
         
         if not org_perm:
             return HTMLResponse("<h1>Organization has no access to BIM</h1>", status_code=403)
             
         org = membership.organization
         
         return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "user_name": user.get("sub"), 
            "user_initials": user.get("sub")[:2].upper(),
            "org_name": org.name,
            "org_id": org.id,
            "role": membership.role
         })
    finally:
        db.close()



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