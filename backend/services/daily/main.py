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
    # Use SessionOps because Daily tables are in Ops DB
    db = database.SessionOps()
    try:
        constraints = [
            ("daily_teams", "daily_teams_owner_id_fkey"),
            ("daily_teams", "daily_teams_organization_id_fkey"),
            ("daily_projects", "daily_projects_organization_id_fkey")
        ]
        results = []
        for table, cons in constraints:
            try:
                # Use raw connection for DDL if needed, or session execute
                db.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {cons}"))
                results.append(f"Dropped {cons}")
            except Exception as e:
                results.append(f"Error {cons}: {str(e)}")
        db.commit()
        print(f"✅ [STARTUP] DB Fix Result: {results}")
        return {"status": "done", "results": results}
    finally:
        db.close()

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
    teams = database.get_user_teams(user_id, organization_id=org_id)
    
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
    # If explicit team_id provided, use it.
    # If new_team_name provided, create team first.
    final_team_id = team_id
    
    if new_team_name and org_id:
        # Create new team
        # Members should include creator (user_id) + selected members
        initial_members = [user_id]
        if members:
            initial_members.extend(members)
        # Deduplicate
        initial_members = list(set(initial_members))
        
        # We need a function to create team with members. 
        # Existing database.create_daily_team takes 'members' list? 
        # Let's check database.py signature. It takes 'members=[owner_id]' by default.
        # We should update database.create_daily_team or manually add members.
        # For now, let's assume create_daily_team sets owner as member.
        # We might need to update members column after creation if it supports it.
        # database.create_daily_team signature: (name, owner_id, organization_id, members)
        team = database.create_daily_team(new_team_name, user_id, organization_id=org_id, members=initial_members)
        final_team_id = team.id
        
        # Update team members if we have extra members
        # We can implement database.update_daily_team_members or similar.
        # Since I can't easily change database.py signature without checking usages,
        # I'll rely on a new db helper or direct update if I had access.
        # Actually, let's just modify the team object if Session is active? No, session closed.
        # I'll add a helper or update database.py update_daily_team if exists.
        # Checking database.py: create_daily_team sets members=[owner_id].
        # There is no update_daily_team_members exposed.
        # I'll just rely on creating the project for now, and maybe update members later if I add that helper.
        # Wait, if I can't add members, the feature "Assign Team" (with multiple users) fails.
        # I MUST update database.create_daily_team to accept members list.
        # See next step. I will update database.py first to accept members list.

    proj = database.create_daily_project(final_team_id, name, user_id, organization_id=org_id, bim_project_id=bim_project_id)
    return {"id": proj.id, "name": proj.name}

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
