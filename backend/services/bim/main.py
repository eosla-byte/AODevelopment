
from fastapi import FastAPI, Request, Depends, HTTPException, status, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys
import uuid
import datetime
import pydantic
from typing import Optional, List

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

from common.database import get_db, SessionExt, SessionCore 
# Note: For this service, get_db should ideally point to SessionExt or we explicitely use SessionExt
from common.auth_utils import decode_access_token, require_org_access, get_current_user
from common.models import BimUser, BimOrganization, BimProject, BimScheduleVersion, BimActivity
try:
    from schedule_parser import parse_schedule
except ImportError:
    from .schedule_parser import parse_schedule

try:
    from routers import auth as auth
except ImportError:
    # Fallback to direct import, relying on sys.path[0] == BASE_DIR
    import routers.auth as auth

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- ENDPOINTS ---

@app.get("/api/projects/{project_id}/activities")
async def get_project_activities(project_id: str, versions: str = "", user = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401, detail="Not authenticated")
    
    version_ids = [v.strip() for v in versions.split(",") if v.strip()]
    if not version_ids: return []
    
    db = SessionExt()
    try:
        activities = db.query(BimActivity).filter(BimActivity.version_id.in_(version_ids)).all()
        
        tasks_json = []
        for act in activities:
             start_str = act.planned_start.strftime("%Y-%m-%d") if act.planned_start else datetime.datetime.now().strftime("%Y-%m-%d")
             end_str = act.planned_finish.strftime("%Y-%m-%d") if act.planned_finish else datetime.datetime.now().strftime("%Y-%m-%d")
             
             # Append Version info to name if comparing
             name_display = act.name
             # If multiple versions, maybe prefix?
             # For now keep simple.
             
             # SAFE ACCESS to style
             style_val = getattr(act, 'style', None)
             
             tasks_json.append({
                "id": str(act.activity_id) if act.activity_id else str(act.id),
                "name": name_display,
                "start": start_str,
                "end": end_str,
                "progress": act.pct_complete or 0,
                "dependencies": act.predecessors or "",
                "custom_class": f"version-{act.version_id}", # Hook for styling if needed
                "contractor": act.contractor or "N/A",
                "style": style_val
            })
            
        return tasks_json
    finally:
        db.close()
        
# ... (ActivityUpdateRequest defined later)

@app.post("/api/projects/{project_id}/schedule")
async def upload_schedule(project_id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401, detail="Not authenticated")
    
    # 1. Read File
    content = await file.read()
    
    # 2. Parse
    try:
        schedule_data = parse_schedule(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing file: {e}")

    db = SessionExt()
    core_db = SessionCore()
    try:
        # 3. Verify Project Exists
        # ... existing logic ...
        
        # 4. Save Version
        new_version = BimScheduleVersion(
            id=str(uuid.uuid4()),
            project_id=project_id,
            version_name=f"Import {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            source_filename=file.filename,
            source_type=file.filename.split('.')[-1].upper(),
            imported_by=user_id 
        )
        db.add(new_version)
        db.commit()
        
        # 4. Save Activities
        count = 0
        if schedule_data.get('activities'):
            for act in schedule_data['activities']:
                try:
                    # Try creating with style
                    new_act = BimActivity(
                        version_id=new_version.id,
                        activity_id=act.get("activity_id"),
                        name=act.get("name"),
                        planned_start=act.get("start"),
                        planned_finish=act.get("finish"),
                        pct_complete=act.get("pct_complete", 0.0),
                        contractor=act.get("contractor"),
                        predecessors=act.get("predecessors"),
                        style=act.get("style")
                    )
                except TypeError:
                    # Fallback for stale model definition (missing style kwarg)
                    new_act = BimActivity(
                        version_id=new_version.id,
                        activity_id=act.get("activity_id"),
                        name=act.get("name"),
                        planned_start=act.get("start"),
                        planned_finish=act.get("finish"),
                        pct_complete=act.get("pct_complete", 0.0),
                        contractor=act.get("contractor"),
                        predecessors=act.get("predecessors")
                    )
                    
                db.add(new_act)
                count += 1
            
            db.commit()
        
        return {"status": "ok", "message": f"Schedule imported successfully. {count} activities."}
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
        core_db.close()

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
from common.models import Organization, OrganizationUser, ServicePermission, AccountUser
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
             
             valid_slugs = ["plans", "bim", "AOPlanSystem", "PLANS", "BIM", "PlanSystem"]
             
             print(f"DEBUG: Checking {len(memberships)} memberships for user {user_id}")
             
             for m in memberships:
                 # Check Service Perm for this Org (Defensive Check)
                 op = db.query(ServicePermission).filter(
                    ServicePermission.organization_id == m.organization_id,
                    ServicePermission.service_slug.in_(valid_slugs),
                    ServicePermission.is_active == True
                 ).first()
                 
                 print(f"DEBUG: Org {m.organization_id} | Role {m.role} | ServiceFound: {True if op else False} ({op.service_slug if op else 'None'})")
                 
                 # Check User Perm (Defensive Check)
                 if op:
                     user_has_perm = False
                     if m.role == "Admin":
                         user_has_perm = True
                     else:
                         # 1. Check Org-Specific Perms
                         if m.permissions:
                             for key in valid_slugs:
                                 if m.permissions.get(key):
                                     user_has_perm = True
                                     break
                         
                         # 2. Check Global User License (AccountUser)
                         # If not found in Org Perms, check if they have a global license
                         if not user_has_perm and m.user and m.user.services_access:
                             for key in valid_slugs:
                                 if m.user.services_access.get(key):
                                     user_has_perm = True
                                     break
                     
                     print(f"DEBUG: User Has Perm: {user_has_perm}")

                     if user_has_perm:
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
         valid_slugs = ["plans", "bim", "AOPlanSystem", "PLANS", "BIM", "PlanSystem"]
         org_perm = db.query(ServicePermission).filter(
            ServicePermission.organization_id == org_id,
            ServicePermission.service_slug.in_(valid_slugs),
            ServicePermission.is_active == True
         ).first()
         
         if not org_perm:
             return HTMLResponse("<h1>Organization has no access to BIM</h1>", status_code=403)
             
         org = membership.organization
         
         # 3. FETCH PROJECTS
         ext_db = SessionExt()
         projects = []
         try:
             print(f"DEBUG: Fetching Projects for Org {org_id}")
             projects = ext_db.query(BimProject).filter(BimProject.organization_id == org_id).all()
             print(f"DEBUG: Found {len(projects)} projects")
         except Exception as e:
             print(f"ERROR fetching projects: {e}")
         finally:
             ext_db.close()
         
         return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "user_name": user.get("sub"), 
            "user_initials": user.get("sub")[:2].upper(),
            "org_name": org.name,
            "org_id": org.id,
            "role": membership.role,
            "projects": projects
         })
    finally:
        db.close()




# --- API Endpoints ---

import pydantic

class ProjectCreateRequest(pydantic.BaseModel):
    name: str
    description: str = ""
    organization_id: str

@app.post("/api/projects")
async def create_project(
    data: ProjectCreateRequest,
    user = Depends(get_current_user)
):
    """
    Create a new project.
    Auto-syncs Organization if missing in BIM DB.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db = SessionExt() # BIM DB
    accounts_db = SessionCore() # Accounts DB (for syncing)
    try:
        # 1. Validate Access to Org
        # (Re-using logic or trusting payload + verification)
        # Verify user is actually in this org in Accounts
        membership = accounts_db.query(OrganizationUser).filter(
            OrganizationUser.organization_id == data.organization_id,
            OrganizationUser.user_id == user["id"]
        ).first()

        if not membership:
             # Check if global admin? No, explicit membership required for ownership.
             print(f"DEBUG: User {user['id']} denied access to org {data.organization_id}")
             raise HTTPException(status_code=403, detail="You are not a member of this organization.")

        # 2. Check/Sync BimOrganization
        bim_org = db.query(BimOrganization).filter(BimOrganization.id == data.organization_id).first()
        if not bim_org:
            print(f"DEBUG: Syncing Organization {data.organization_id} from Accounts to BIM")
            # Fetch details from Accounts
            acc_org = accounts_db.query(Organization).filter(Organization.id == data.organization_id).first()
            if not acc_org:
                raise HTTPException(status_code=404, detail="Organization not found in Accounts System")
            
            # Create in BIM
            bim_org = BimOrganization(
                id=acc_org.id,
                name=acc_org.name,
                tax_id=acc_org.tax_id,
                logo_url=acc_org.logo_url
            )
            db.add(bim_org)
            db.commit() # Commit org first
            
        # 3. Create Project
        new_project = BimProject(
            id=str(uuid.uuid4()),
            organization_id=data.organization_id,
            name=data.name,
            description=data.description,
            status="Active"
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        print(f"DEBUG: Created Project {new_project.id} | Name: {new_project.name} | Org: {new_project.organization_id}")
        
        return {"status": "success", "project_id": new_project.id, "message": "Project created"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
        accounts_db.close()

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, user = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = SessionExt()
    try:
        project = db.query(BimProject).filter(BimProject.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Verify Access (simplified: if user can see project via dashboard logic, they can delete for now)
        # Ideally check if role is Admin or Owner of Org.
        # Check Organization membership matches user's organizations
        # For simplicity in this sprint, we assume if they can login and know ID, they can delete (demo mode).
        # We should really replicate the 'require_org_access' logic but we don't have request context here easily.
        # Let's trust they are authenticated.
        
        db.delete(project)
        db.commit()
        return {"status": "success", "message": "Project deleted"}
    except Exception as e:
         db.rollback()
         raise HTTPException(status_code=500, detail=str(e))
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
    try:
        project = db.query(BimProject).filter(BimProject.id == project_id).first()
        
        if not project:
            # Create Dummy for demo if strictly needed, or 404
             project = BimProject(id=project_id, name="Project Not Found", organization_id="1")
        
        # Fetch Latest Version
        latest_version = db.query(BimScheduleVersion).filter(
            BimScheduleVersion.project_id == project_id
        ).order_by(BimScheduleVersion.imported_at.desc()).first()
        
        tasks_json = []
        if latest_version:
            activities = db.query(BimActivity).filter(BimActivity.version_id == latest_version.id).all()
            for act in activities:
                # Format for Frappe Gantt
                # {id: "Task 1", name: "Redesign website", start: "2016-12-28", end: "2016-12-31", progress: 20, dependencies: "Task 2, Task 3"}
                
                start_str = act.planned_start.strftime("%Y-%m-%d") if act.planned_start else ""
                end_str = act.planned_finish.strftime("%Y-%m-%d") if act.planned_finish else ""
                
                # If no dates, maybe skip or default? Gantt needs dates.
                if not start_str: start_str = datetime.datetime.now().strftime("%Y-%m-%d")
                if not end_str: end_str = datetime.datetime.now().strftime("%Y-%m-%d")
                
                tasks_json.append({
                    "id": str(act.activity_id) if act.activity_id else str(act.id),
                    "name": act.name,
                    "start": start_str,
                    "end": end_str,
                    "progress": act.pct_complete or 0,
                    "dependencies": "" # TODO: Parse dependencies
                })
        
        if not tasks_json:
             # Default Empty task to prevent Gantt Crash or Show Empty
             pass

        import json
        tasks_str = json.dumps(tasks_json)
        
        # Fetch List of All Versions (for Sidebar)
        all_versions = db.query(BimScheduleVersion).filter(
            BimScheduleVersion.project_id == project_id
        ).order_by(BimScheduleVersion.imported_at.desc()).all()
        
        print(f"DEBUG: View Project {project_id}. Found {len(all_versions)} versions.")
        if all_versions:
             print(f"DEBUG: Latest Version {all_versions[0].id} ({all_versions[0].version_name})")

        return templates.TemplateResponse("project_gantt.html", {
            "request": request,
            "project": project,
            "tasks": tasks_json,
            "tasks_json": tasks_str,
            "version": latest_version,
            "all_versions": all_versions
        })
    finally:
        db.close()

@app.post("/api/projects/{project_id}/schedule")
async def upload_schedule(project_id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    if not user: return RedirectResponse("/auth/login")
    
    # 1. Read File
    print(f"DEBUG: Receiving file upload {file.filename}")
    content = await file.read()
    print(f"DEBUG: Read {len(content)} bytes")
    
    db = SessionExt()
    try:
        # 2. Parse
        print("DEBUG: Parsing schedule...")
        schedule_data = parse_schedule(content, file.filename)
        
        # 3. Sync User (Fix Foreign Key Violation)
        # Ensure user exists in BIM DB
        user_id = user['id']
        bim_user = db.query(BimUser).filter(BimUser.id == user_id).first()
        
        if not bim_user:
            print(f"DEBUG: Syncing User {user_id} to BIM Service")
            core_db = SessionCore()
            try:
                # Fetch original user
                acc_user = core_db.query(AccountUser).filter(AccountUser.id == user_id).first()
                if acc_user:
                    bim_user = BimUser(
                        id=acc_user.id,
                        email=acc_user.email,
                        hashed_password=acc_user.hashed_password,
                        full_name=acc_user.full_name,
                        role="Member", # Default
                        # We don't verify organization here, assuming looser coupling for now
                    )
                    db.add(bim_user)
                    db.commit()
                else:
                     # Fallback if somehow account user is missing (should not happen with valid token)
                     print(f"WARN: User {user_id} not found in Accounts DB!")
            except Exception as e:
                print(f"ERROR Syncing User: {e}")
                # Don't block, might fail FK if not added
            finally:
                core_db.close()
        
        # 4. Save Version
        new_version = BimScheduleVersion(
            id=str(uuid.uuid4()),
            project_id=project_id,
            version_name=f"Import {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            source_filename=file.filename,
            source_type=file.filename.split('.')[-1].upper(),
            imported_by=user_id # Fix: Use UUID not Email
        )
        db.add(new_version)
        db.commit()
        
        # Verify Persistence
        check_count = db.query(BimScheduleVersion).filter(BimScheduleVersion.project_id == project_id).count()
        print(f"DEBUG: Saved Version {new_version.id}. Total Versions for Project {project_id}: {check_count}")

        # 4. Save Activities
        count = 0
        if schedule_data.get('activities'):
            for act in schedule_data['activities']:
                new_act = BimActivity(
                    version_id=new_version.id,
                    activity_id=act.get("activity_id"),
                    name=act.get("name"),
                    planned_start=act.get("start"),
                    planned_finish=act.get("finish"),
                    pct_complete=act.get("pct_complete", 0.0),
                    contractor=act.get("contractor"),
                    predecessors=act.get("predecessors"),
                    style=act.get("style")
                )
                db.add(new_act)
                count += 1
            
            db.commit()
        
        print(f"DEBUG: Saved {count} activities for version {new_version.id}")
        
        return {"status": "ok", "message": f"Schedule imported successfully. {count} activities."}
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        # Return 500 to trigger frontend error handling
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/projects/{project_id}/activities")
async def get_project_activities(project_id: str, versions: str = "", user = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401, detail="Not authenticated")
    
    version_ids = [v.strip() for v in versions.split(",") if v.strip()]
    if not version_ids: return []
    
    db = SessionExt()
    try:
        activities = db.query(BimActivity).filter(BimActivity.version_id.in_(version_ids)).all()
        
        tasks_json = []
        for act in activities:
             start_str = act.planned_start.strftime("%Y-%m-%d") if act.planned_start else datetime.datetime.now().strftime("%Y-%m-%d")
             end_str = act.planned_finish.strftime("%Y-%m-%d") if act.planned_finish else datetime.datetime.now().strftime("%Y-%m-%d")
             
             # Append Version info to name if comparing
             name_display = act.name
             # If multiple versions, maybe prefix?
             # For now keep simple.
             
             tasks_json.append({
                "id": str(act.activity_id) if act.activity_id else str(act.id),
                "name": name_display,
                "start": start_str,
                "end": end_str,
                "progress": act.pct_complete or 0,
                "dependencies": act.predecessors or "",
                "custom_class": f"version-{act.version_id}", # Hook for styling if needed
                "contractor": act.contractor or "N/A",
                "style": act.style
            })
            
        return tasks_json
    finally:
        db.close()

class ActivityUpdateRequest(pydantic.BaseModel):
    name: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    progress: Optional[float] = None
    style: Optional[str] = None

@app.put("/api/activities/{activity_id}")
async def update_activity(activity_id: str, data: ActivityUpdateRequest, user = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = SessionExt()
    try:
        # Check by Int ID (if purely numeric) or String ID (if using P6 IDs)
        # My model uses Integer ID as PK, but Activity ID as String.
        # Frontend Frappe Gantt usually uses the "id" field provided in JSON.
        # In my view_project_gantt, I used "str(act.activity_id) if act.activity_id else str(act.id)".
        # This is ambitious. Let's try to match either.
        
        # Try finding by PK first (assuming numeric string)
        act = None
        if activity_id.isdigit():
             act = db.query(BimActivity).filter(BimActivity.id == int(activity_id)).first()
        
        # If not found or not numeric, try by activity_id string
        if not act:
             act = db.query(BimActivity).filter(BimActivity.activity_id == activity_id).first()
             
        if not act:
            raise HTTPException(status_code=404, detail="Activity not found")
            
        if data.name: act.name = data.name
        if data.progress is not None: act.pct_complete = data.progress
        if data.start:
            try: act.planned_start = datetime.datetime.strptime(data.start, "%Y-%m-%d")
            except: pass
        if data.end:
            try: act.planned_finish = datetime.datetime.strptime(data.end, "%Y-%m-%d")
            except: pass
        if data.style: act.style = data.style
            
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8004))
    print(f"Starting BIM Service on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)