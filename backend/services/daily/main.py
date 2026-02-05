from fastapi import FastAPI, Depends, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os

try:
    from .common import database
    # Import specific models to ensure they are registered with Base
    from .common.models import DailyTeam, DailyProject, DailyColumn, DailyTask, DailyComment, DailyMessage
except ImportError:
    # Fallback to absolute if running from root without package context (dev)
    from common import database
    from common.models import DailyTeam, DailyProject, DailyColumn, DailyTask, DailyComment, DailyMessage

try:
    from .aodev import connector as aodev
except ImportError:
    import aodev as aodev_module
    aodev = aodev_module.connector

app = FastAPI(title="AOdailyWork")

app = FastAPI(title="AOdailyWork")

# ALLOW CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# DEPENDENCIES
# -----------------------------------------------------------------------------

def get_current_user_id(request: Request):
    # For MVP, we accept 'X-User-Email' or 'X-User-ID' header.
    # PROD: Verify JWT.
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        # Fallback for dev - if testing via browser without headers, maybe query param?
        # Or hardcode a demo user if none provided?
        return "demo-user-id" 
    return user_id

def get_current_org_id(request: Request):
    # Organization Context Header
    # If missing, we might default to None (Global/Personal) or Error depending on strictness.
    # For alignment, we prefer it to be present for "Company" views.
    org_id = request.headers.get("X-Organization-ID")
    return org_id

# -----------------------------------------------------------------------------
# ROUTES
# -----------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AOdailyWork"}

def run_db_fix():
    print("🔧 [STARTUP] Checking Database Schema Constraints...")
    from sqlalchemy import text
    try:
        db = database.SessionOps()
        # 1. Drop Invalid Constraints
        # Drop Constraint if exists (Self-healing for cross-db FKs)
        actions = []
        try:
            db.execute(text("ALTER TABLE daily_teams DROP CONSTRAINT IF EXISTS daily_teams_owner_id_fkey"))
            actions.append("Dropped daily_teams_owner_id_fkey")
            db.execute(text("ALTER TABLE daily_teams DROP CONSTRAINT IF EXISTS daily_teams_organization_id_fkey"))
            actions.append("Dropped daily_teams_organization_id_fkey")
            # Also check daily_projects if necessary
            db.execute(text("ALTER TABLE daily_projects DROP CONSTRAINT IF EXISTS daily_projects_organization_id_fkey"))
            actions.append("Dropped daily_projects_organization_id_fkey")
            
            # 2. Check for Missing Columns (Schema Mismatch Fix)
            # Check bim_project_id in daily_projects
            try:
                db.execute(text("SELECT bim_project_id FROM daily_projects LIMIT 1"))
            except Exception:
                db.rollback()
                print("⚠️ [SCHEMA FIX] Adding missing column: bim_project_id to daily_projects")
                db.execute(text("ALTER TABLE daily_projects ADD COLUMN IF NOT EXISTS bim_project_id VARCHAR"))
                actions.append("Added bim_project_id column")
                db.commit()

            db.commit()
            print(f"✅ [STARTUP] DB Fix Result: {actions}")
        except Exception as e:
            print(f"⚠️ [STARTUP] DB Fix Warning: {e}")
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        print(f"❌ [STARTUP] DB Fix Failed: {e}")

@app.on_event("startup")
def startup_event():
    print("🚀 [STARTUP] Daily Service Starting - Version POJO_FIX_V2")
    run_db_fix()

@app.get("/fix-db")
def fix_database_schema():
    return run_db_fix()

@app.get("/init")
def init_app(user_id: str = Depends(get_current_user_id), org_id: str = Depends(get_current_org_id)):
    """
    Bootstrap the app. Returns user's teams and projects.
    """
    database.init_user_daily_setup(user_id)
    # USE SAFE INLINED RETRIEVAL
    teams = get_user_teams_safe(user_id, organization_id=org_id)
    
    # Format for Frontend
    teams_data = []
    for t in teams:
        teams_data.append({
            "id": t.id,
            "name": t.name,
            "projects": [{"id": p.id, "name": p.name} for p in t.projects]
        })
        
    return {
        "user_id": user_id,
        "teams": teams_data
    }

@app.post("/teams")
def create_team(
    name: str = Body(..., embed=True), 
    user_id: str = Depends(get_current_user_id),
    org_id: str = Depends(get_current_org_id)
):
    team = database.create_daily_team(name, user_id, organization_id=org_id)
    return {"id": team.id, "name": team.name}

# -----------------------------------------------------------------------------
# SAFE INLINED DB HELPERS (Bypass Stale Cache)
# -----------------------------------------------------------------------------

def create_daily_team_safe(name: str, owner_id: str, organization_id: str = None, members: List[str] = None):
    import uuid
    import types
    from sqlalchemy import text
    
    db = database.SessionOps()
    try:
        new_id = str(uuid.uuid4())
        initial_members = [owner_id]
        if members:
            initial_members.extend(members)
        initial_members = list(set(initial_members))

        team = DailyTeam(
            id=new_id, 
            name=name, 
            owner_id=owner_id, 
            organization_id=organization_id,
            members=initial_members
        )
        db.add(team)
        try:
            db.commit()
        except Exception as e:
            err_str = str(e).lower()
            if "foreignkey" in err_str:
                print("⚠️ [INLINED] Dropping Constraints...")
                db.rollback()
                db.execute(text("ALTER TABLE daily_teams DROP CONSTRAINT IF EXISTS daily_teams_owner_id_fkey"))
                db.execute(text("ALTER TABLE daily_teams DROP CONSTRAINT IF EXISTS daily_teams_organization_id_fkey"))
                db.commit()
                db.add(team)
                db.commit()
            else:
                raise e
        
        # KEY FIX: Return POJO
        return types.SimpleNamespace(id=team.id, name=team.name)
    finally:
        db.close()

def create_daily_project_safe(team_id: str, name: str, user_id: str, organization_id: str = None, bim_project_id: str = None):
    import uuid
    import types
    
    db = database.SessionOps()
    try:
        new_id = str(uuid.uuid4())
        proj = DailyProject(
            id=new_id, 
            team_id=team_id, 
            name=name, 
            created_by=user_id,
            organization_id=organization_id,
            bim_project_id=bim_project_id,
            settings={"background": "default"}
        )
        
        cols = ["To Do", "In Progress", "Done"]
        for idx, title in enumerate(cols):
            c_id = str(uuid.uuid4())
            col = DailyColumn(id=c_id, project_id=new_id, title=title, order_index=idx)
            db.add(col)
            
        db.add(proj)
        db.commit()
        
        # KEY FIX: Return POJO
        return types.SimpleNamespace(id=proj.id, name=proj.name)
    finally:
        db.close()

def get_user_teams_safe(user_id: str, organization_id: str = None):
    import types
    # Ensure fresh session
    db = database.SessionOps()
    try:
        # We need to filter manually because JSON query in SQLite/Postgres differs and we want safety
        query = db.query(DailyTeam)
        if organization_id:
            query = query.filter(DailyTeam.organization_id == organization_id)
        
        all_teams = query.all()
        # Filter: check if user_id is in members list
        # We assume members is a JSON list of strings
        user_teams_orm = []
        for t in all_teams:
            mems = t.members or []
            if user_id in mems:
                user_teams_orm.append(t)
        
        # Copia a POJO
        result = []
        for t in user_teams_orm:
            # Manually fetch projects to avoid lazy load issues after session close
            # and to bypass stale cache
            projs = db.query(DailyProject).filter(DailyProject.team_id == t.id).all()
            safe_projs = [types.SimpleNamespace(id=p.id, name=p.name) for p in projs]
            
            safe_team = types.SimpleNamespace(
                id=t.id, 
                name=t.name, 
                projects=safe_projs
            )
            result.append(safe_team)
            
        print(f"✅ [INLINED RETRIEVAL] Found {len(result)} teams for user {user_id}")
        return result
    finally:
        db.close()

@app.post("/projects")
def create_project(
    team_id: str = Body(None), 
    name: str = Body(...), 
    bim_project_id: str = Body(None),
    new_team_name: str = Body(None),
    members: List[str] = Body(None), # List of User IDs for new team
    user_id: str = Depends(get_current_user_id),
    org_id: str = Depends(get_current_org_id)
):
    print(f"🚀 [API] Creating Project: {name} (User: {user_id}, Org: {org_id})")
    try:
        final_team_id = team_id
        
        if new_team_name and org_id:
            # Use SAFE inlined function
            team = create_daily_team_safe(new_team_name, user_id, organization_id=org_id, members=members)
            final_team_id = team.id
            print(f"✅ Team Created Safe: {final_team_id}")

        # Use SAFE inlined function
        proj = create_daily_project_safe(final_team_id, name, user_id, organization_id=org_id, bim_project_id=bim_project_id)
        print(f"✅ Project Created Safe: {proj.id}")
        return {"id": proj.id, "name": proj.name}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/org-users")
def get_organization_users(org_id: str = Depends(get_current_org_id)):
    if not org_id:
        return []
    print(f"🔍 [API] /org-users requested for Org: {org_id}")
    users = database.get_org_users(org_id)
    print(f"✅ [API] Found {len(users)} users")
    return users

@app.get("/my-organizations")
def get_my_organizations(email: str):
    print(f"🔍 [API] /my-organizations requested for: {email}")
    orgs = database.get_user_organizations(email)
    print(f"✅ [API] Found {len(orgs)} orgs")
    return orgs

@app.get("/bim-projects")
def get_available_bim_projects(org_id: str = Depends(get_current_org_id)):
    if not org_id:
        return []
    # Fetching Project Profiles (resources_projects) instead of bim_projects
    # because that is what the user understands as "Projects" to link.
    print(f"🔍 [API] /bim-projects requested for Org: {org_id}")
    projects = database.get_org_projects(org_id)
    print(f"✅ [API] Found {len(projects)} projects")
    return [{"id": p.id, "name": p.name} for p in projects]

@app.get("/projects/{project_id}/board")
def get_project_board_view(project_id: str):
    proj = database.get_daily_project_board(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return {
        "id": proj.id,
        "name": proj.name,
        "columns": [
            {
                "id": c.id,
                "title": c.title,
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "priority": t.priority,
                        "assignees": t.assignees
                    }
                    for t in c.tasks
                ]
            }
            for c in proj.columns
        ]
    }

def delete_daily_project_safe(project_id: str, user_id: str):
    db = database.SessionOps()
    try:
        # Check permissions (simple check: if user created it or is in the team)
        # For now, allow deletion if user has access.
        proj = db.query(DailyProject).filter(DailyProject.id == project_id).first()
        if not proj:
            return False
            
        # Delete Project (Cascade should handle children if configured, 
        # but let's be explicit manually for safety if cascade is missing in DB)
        
        # 1. Delete Tasks
        db.query(DailyTask).filter(DailyTask.project_id == project_id).delete()
        # 2. Delete Columns
        db.query(DailyColumn).filter(DailyColumn.project_id == project_id).delete()
        # 3. Delete Messages
        db.query(DailyMessage).filter(DailyMessage.project_id == project_id).delete()
        
        # 4. Delete Project
        db.delete(proj)
        db.commit()
        print(f"✅ [API] Project Deleted: {project_id}")
        return True
    except Exception as e:
        print(f"❌ [API] Delete Failed: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

@app.delete("/projects/{project_id}")
def delete_project(project_id: str, user_id: str = Depends(get_current_user_id)):
    print(f"🚀 [API] Deleting Project: {project_id} (User: {user_id})")
    try:
        # Check if project exists and user has permission?
        # Using SAFE inlined function
        success = delete_daily_project_safe(project_id, user_id)
        if not success:
             raise HTTPException(status_code=404, detail="Project not found")
        return {"status": "deleted", "id": project_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks")
def create_task(
    project_id: str = Body(None),
    column_id: str = Body(None),
    title: str = Body(...),
    priority: str = Body("Medium"),
    user_id: str = Depends(get_current_user_id)
):
    # If direct assignment (Manager mode), project_id might be None?
    # Logic in database.create_daily_task handles None.
    task = database.create_daily_task(project_id, column_id, title, user_id, priority=priority)
    
    # Notify AOdev
    aodev.send_event("TASK_CREATED", {"id": task.id, "title": task.title, "user": user_id})
    
    return {"id": task.id, "title": task.title}

@app.put("/tasks/{task_id}/move")
def move_task(
    task_id: str,
    column_id: str = Body(..., embed=True),
    index: int = Body(0, embed=True)
):
    success = database.update_daily_task_location(task_id, column_id, index)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "moved"}

@app.get("/my-tasks")
def get_my_tasks(user_id: str = Depends(get_current_user_id)):
    tasks = database.get_user_daily_tasks(user_id)
    return [
        {
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "status": t.status,
            "project_id": t.project_id # Frontend can fetch Project Name if needed
        }
        for t in tasks
    ]

@app.get("/chat/{project_id}")
def get_chat(project_id: str):
    msgs = database.get_daily_messages(project_id)
    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else ""
        }
        for m in msgs
    ]

@app.post("/chat/{project_id}")
def send_chat(project_id: str, content: str = Body(..., embed=True), user_id: str = Depends(get_current_user_id)):
    # Trigger deployment for user
    msg = database.add_daily_message(project_id, user_id, content)
    return {"id": msg.id, "status": "sent"}

@app.get("/projects/{project_id}/metrics")
def get_project_metrics_endpoint(project_id: str):
    metrics = database.get_project_metrics(project_id)
    if not metrics:
        return {
            "total_tasks": 0, "pending": 0, "in_progress": 0, "done": 0, 
            "top_user_id": None, "user_stats": {}
        }
    return metrics

# -----------------------------------------------------------------------------
# STATIC FILES & FRONTEND
# -----------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# -----------------------------------------------------------------------------
# STATIC FILES & FRONTEND
# -----------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Path Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# DEBUG LOGGING
print(f"deployment_debug: BASE_DIR={BASE_DIR}")
print(f"deployment_debug: STATIC_DIR={STATIC_DIR}")
if os.path.exists(BASE_DIR):
    print(f"deployment_debug: Listing BASE_DIR: {os.listdir(BASE_DIR)}")

# Mount /assets if it exists, otherwise just log
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
else:
    print(f"deployment_debug: Assets dir missing at {ASSETS_DIR}")

@app.get("/")
async def serve_root():
    # Debug response if file is missing
    index_path = os.path.join(STATIC_DIR, "daily.html")
    if not os.path.exists(index_path):
        # Return debug info to the browser/client to see what's wrong
        return JSONResponse({
            "error": "daily.html not found",
            "path_attempted": index_path,
            "cwd": os.getcwd(),
            "base_dir_contents": os.listdir(BASE_DIR) if os.path.exists(BASE_DIR) else "BASE_DIR missing",
            "static_dir_contents": os.listdir(STATIC_DIR) if os.path.exists(STATIC_DIR) else "STATIC_DIR missing"
        }, status_code=404)
        
    return FileResponse(index_path)

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    # Serve static file if it exists
    file_path = os.path.join(STATIC_DIR, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
        
    # Fallback to SPA entry point
    index_path = os.path.join(STATIC_DIR, "daily.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
        
    return JSONResponse({"detail": "Not Found (SPA Fallback missing)"}, status_code=404)
