from fastapi import FastAPI, Depends, HTTPException, Request, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import uuid
import datetime

try:
    from .common import database
    # Import specific models to ensure they are registered with Base
    from .common.models import DailyTeam, DailyProject, DailyColumn, DailyTask, DailyComment, DailyMessage, DailyChannel
    from .common.auth_utils import decode_access_token
except ImportError:
    # Fallback to absolute if running from root without package context (dev)
    from common import database, models
    from common.models import DailyTeam, DailyProject, DailyColumn, DailyTask, DailyComment, DailyMessage, DailyChannel
    from common.auth_utils import decode_access_token

try:
    from .aodev import connector as aodev
except ImportError:
    import aodev as aodev_module
    aodev = aodev_module.connector

app = FastAPI(title="AOdailyWork")

app = FastAPI(title="AOdailyWork")

# ALLOW CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://daily.somosao.com",
    "https://accounts.somosao.com",
    "https://bim.somosao.com",
    "https://aodev.railway.internal"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# STARTUP MIGRATION
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup_check():
    print("🚀 [Daily] SERVER STARTING - DEPLOYMENT_V_FINAL_FIX_JWT")
    try:
        import jwt
        print(f"✅ [Daily] JWT Module Loaded: {jwt.__file__}")
    except ImportError as e:
        print(f"❌ [Daily] JWT Module NOT FOUND: {e}")
    except Exception as e:
        print(f"❌ [Daily] JWT Import Error: {e}")

@app.on_event("startup")
async def run_migrations():
    print("🔄 [Daily] Checking Schema Migrations...")
    try:
        from sqlalchemy import text
        db = database.SessionOps()
        # Auto-add user_name to daily_comments if missing
        try:
            db.execute(text("ALTER TABLE daily_comments ADD COLUMN user_name VARCHAR"))
            db.commit()
            print("✅ [Daily] Migration: Added 'user_name' to daily_comments")
        except Exception as e:
            db.rollback()
            pass
        finally:
            db.close()
    except Exception as outer:
        print(f"⚠️ [Daily] Migration check failed: {outer}")

# -----------------------------------------------------------------------------
# DEPENDENCIES
# -----------------------------------------------------------------------------

def get_current_user_id(request: Request):
    """
    Strict Auth:
    1. Check Authorization Header (Bearer)
    2. Check cookies (access_token or accounts_access_token)
    3. Decode JWT to get 'sub' (User ID)
    4. If fails/missing -> Return None (Guest Mode) - DO NOT TRUST X-User-ID
    """
    import os
    
    # SAFE IMPORT JWT
    try:
        import jwt
    except ImportError:
        print("❌ [Auth] CRITICAL: PyJWT not installed. Authentication disabled (Guest only).")
        return None
    
    token = None
    token_source = "None"
    
    # 1. Bearer Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
         token = auth_header.split(" ")[1]
         token_source = "Header"
         
    # 2. Cookies (HttpOnly)
    if not token:
        token = request.cookies.get("access_token") or request.cookies.get("accounts_access_token")
        if token:
            token_source = "Cookie"
        
    # HOTFIX: Strip 'Bearer ' prefix if present in cookie (or header)
    if token and token.startswith("Bearer "):
        token = token.split(" ")[1].strip()
        
    if not token:
        # print("⚠️ [Auth] No token found. Guest Mode.")
        return None

    # DEBUG: Token Structure
    dot_count = token.count('.')
    # print(f"🔐 [Auth] Token Source: {token_source} | Dots: {dot_count} | Partial: {token[:10]}...")
    
    if dot_count != 2:
        print(f"❌ [Auth] Invalid JWT Structure (Dots: {dot_count}). Token: {token[:20]}...")
        return None
        
    try:
        # DEBUG: Unverified Inspection
        unverified_header = jwt.get_unverified_header(token)
        # print(f"🕵️ [Auth Debug] Header: {unverified_header}")
        
        # Verify Algorithm
        alg = unverified_header.get('alg')
        if alg != 'HS256':
             print(f"⚠️ [Auth] Unexpected Algorithm: {alg}. Expected HS256.")

        # SECRET KEY ALIGNMENT
        # Accounts service uses: os.getenv("SECRET_KEY", "AO_RESOURCES_SUPER_SECRET_KEY_CHANGE_THIS_IN_PROD")
        # specific hardcoded fallback to match Accounts if env is missing
        SECRET_KEY = os.getenv("SECRET_KEY", "AO_RESOURCES_SUPER_SECRET_KEY_CHANGE_THIS_IN_PROD")
        
        # DECODE JWT (HS256)
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        print("⚠️ [Auth] Token expired.")
        return None
    except jwt.InvalidSignatureError:
        print(f"❌ [Auth] Signature Verification Failed. Used Key: {SECRET_KEY[:4]}... Alg: {alg}")
        return None
    except jwt.InvalidTokenError as e:
        print(f"⚠️ [Auth] Invalid token: {e}")
        return None
    except Exception as e:
        print(f"❌ [Auth] Unexpected JWT Error: {e}")
        return None

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

@app.get("/auth/token")
def get_auth_token(request: Request):
    """
    Exposes the HTTP-Only cookie token to the Frontend application (JS)
    so it can be passed to the BIM Iframe which cannot read the cookie directly due to partitions.
    """
    token = request.cookies.get("accounts_access_token")
    if token and token.startswith("Bearer "):
        token = token.split(" ")[1]
    return {"token": token}

def run_db_fix():
    print("🔧 [STARTUP] Checking Database Schema Constraints...")
    from sqlalchemy import text
    print("🚀 [STARTUP] Daily Service Starting - Version V7.6-QueryFix")
    
    try:
        index_path = os.path.join(STATIC_DIR, "daily.html")
        if os.path.exists(index_path):
             with open(index_path, "r") as f:
                 content = f.read()
                 print(f"🔍 [DEBUG] daily.html loaded. Length: {len(content)}")
                 # Extract script src
                 import re
                 scripts = re.findall(r'src="([^"]+)"', content)
                 print(f"🔍 [DEBUG] daily.html SCRIPTS: {scripts}")
        else:
            print("⚠️ [DEBUG] daily.html NOT FOUND during startup")
    except Exception as e:
        print(f"⚠️ [DEBUG] Error reading daily.html: {e}")

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

            # Chat Fixes
            try:
                # Create Channels Table if not exists
                db.execute(text("""
                    CREATE TABLE IF NOT EXISTS daily_channels (
                        id VARCHAR PRIMARY KEY,
                        project_id VARCHAR,
                        name VARCHAR NOT NULL,
                        type VARCHAR DEFAULT 'text',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(project_id) REFERENCES daily_projects(id)
                    )
                """))
                actions.append("Ensured daily_channels table")
                db.commit()
                
                # Check channel_id in daily_messages
                try:
                    db.execute(text("SELECT channel_id FROM daily_messages LIMIT 1"))
                except Exception:
                    db.rollback()
                    db.execute(text("ALTER TABLE daily_messages ADD COLUMN IF NOT EXISTS channel_id VARCHAR REFERENCES daily_channels(id)"))
                    actions.append("Added channel_id to daily_messages")
                    db.commit()

                # Check attachments in daily_messages
                try:
                    db.execute(text("SELECT attachments FROM daily_messages LIMIT 1"))
                except Exception:
                    db.rollback()
                    db.execute(text("ALTER TABLE daily_messages ADD COLUMN IF NOT EXISTS attachments JSON DEFAULT '[]'"))
                    actions.append("Added attachments to daily_messages")
                    db.commit()
                    
                # Check thread_root_id in daily_messages
                try:
                    db.execute(text("SELECT thread_root_id FROM daily_messages LIMIT 1"))
                except Exception:
                    db.rollback()
                    db.execute(text("ALTER TABLE daily_messages ADD COLUMN IF NOT EXISTS thread_root_id INTEGER"))
                    actions.append("Added thread_root_id to daily_messages")
                    db.commit()

                # [NEW] Check started_at in daily_tasks
                try:
                    db.execute(text("SELECT started_at FROM daily_tasks LIMIT 1"))
                except Exception:
                    db.rollback()
                    db.execute(text("ALTER TABLE daily_tasks ADD COLUMN IF NOT EXISTS started_at TIMESTAMP"))
                    actions.append("Added started_at to daily_tasks")
                    db.commit()

                # [NEW] Check completed_at in daily_tasks
                try:
                    db.execute(text("SELECT completed_at FROM daily_tasks LIMIT 1"))
                except Exception:
                    db.rollback()
                    db.execute(text("ALTER TABLE daily_tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP"))
                    actions.append("Added completed_at to daily_tasks")
                    db.commit()

            except Exception as e:
                print(f"⚠️ [SCHEMA FIX] Chat Schema Warning: {e}")
                db.rollback()

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
    print("🚀 [STARTUP] Daily Service Starting - Version V5_KANBAN_FORCED")
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
            "projects": [{
                "id": p.id, 
                "name": p.name, 
                "channel_count": getattr(p, 'channel_count', 0),
                "created_at": getattr(p, 'created_at', None)
            } for p in t.projects]
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
            col = DailyColumn(id=c_id, project_id=new_id, title=title, order_index=idx)
            db.add(col)
            
        # Create Default Channel #general
        chan_id = str(uuid.uuid4())
        chan = DailyChannel(id=chan_id, project_id=new_id, name="general", type="text")
        db.add(chan)
            
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
            
            safe_projs = []
            for p in projs:
                # Count channels manually (avoid lazy load error)
                chan_count = db.query(DailyChannel).filter(DailyChannel.project_id == p.id).count()
                
                safe_projs.append(types.SimpleNamespace(
                    id=p.id, 
                    name=p.name, 
                    channel_count=chan_count
                ))
            
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
                        "assignees": t.assignees,
                        "comment_count": len(t.comments or []),
                        "attachment_count": len(t.attachments or [])
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
        
        # 4. Delete Channels
        db.query(DailyChannel).filter(DailyChannel.project_id == project_id).delete()
        
        # 5. Delete Project
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
    
    # Notify AOdev (task is now a dict)
    aodev.send_event("TASK_CREATED", {"id": task["id"], "title": task["title"], "user": user_id})
    
    return {"id": task["id"], "title": task["title"]}

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
    ]

@app.patch("/tasks/{task_id}")
def update_task_details(
    task_id: str,
    title: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    priority: Optional[str] = Body(None),
    status: Optional[str] = Body(None),
    due_date: Optional[str] = Body(None),   # ISO Format
    assignees: Optional[List[str]] = Body(None),
    user_id: str = Depends(get_current_user_id)
):
    import datetime
    db = database.SessionOps()
    try:
        task = db.query(DailyTask).filter(DailyTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        if title is not None: task.title = title
        if description is not None: task.description = description
        if priority is not None: task.priority = priority
        if status is not None: task.status = status
        
        # Date Handling: due_date
        if due_date is not None:
             try:
                 if due_date == "":
                     task.due_date = None
                 else:
                     task.due_date = datetime.datetime.fromisoformat(due_date.replace("Z", "+00:00"))
             except ValueError:
                 pass 

        if assignees is not None: task.assignees = assignees
        
        task.updated_at = datetime.datetime.now()
        db.commit()
        
        # Return updated task POJO
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "assignees": task.assignees or []
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/tasks/{task_id}/comments")
def add_task_comment(
    task_id: str,
    content: str = Body(..., embed=True),
    guest_label: str = Body(None, embed=True), # Explicit guest name from UI if unauthed
    user_id: str = Depends(get_current_user_id),
    request: Request = None
):
    import datetime
    db = database.SessionOps()
    try:
        # Verify task exists
        task = db.query(DailyTask).filter(DailyTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        # Timezone: Store in UTC (Best Practice)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # DETERMINE AUTHOR
        final_user_id = None
        final_user_name = None
        author_type = "guest"
        
        if user_id:
             # Authenticated User
             final_user_id = user_id
             author_type = "user"
             # user_name left as None, to be resolved via get_user_map
        else:
             # Guest
             final_user_id = None 
             final_user_name = guest_label or "Guest"
             author_type = "guest"

        comment = DailyComment(
            task_id=task_id,
            user_id=final_user_id, # Null if guest
            user_name=final_user_name, # "Guest X" or Null (if user)
            content=content,
            created_at=now_utc
        )
        db.add(comment)
        db.commit()

        # RETURN PAYLOAD (With Resolved Author)
        # Attempt immediate resolution for UX
        display_name = final_user_name or "Guest"
        if final_user_id:
             try:
                 u_map = get_user_map([final_user_id])
                 if final_user_id in u_map:
                      display_name = u_map[final_user_id]
                 else:
                      display_name = "Unknown User"
             except:
                 display_name = "Unknown User"
                 pass

        author_data = {
             "id": final_user_id,
             "type": author_type,
             "displayName": display_name,
             "avatarUrl": None
        }
        
        return {
            "id": comment.id,
            "content": comment.content,
            "createdAt": comment.created_at.isoformat(), # UTC with Z
            "author": author_data
        }
    finally:
        db.close()
        

def get_user_map(user_ids: List[str]):
    """Helper to fetch user names from Core DB"""
    if not user_ids: return {}
    db = database.SessionCore()
    try:
        # Use AccountUser for ID-based lookup
        users = db.query(models.AccountUser).filter(models.AccountUser.id.in_(user_ids)).all()
        user_map = {u.id: u.full_name for u in users}
        
        # Fallback: check AppUser just in case some IDs are emails
        missing_ids = [uid for uid in user_ids if uid not in user_map]
        if missing_ids:
             app_users = db.query(models.AppUser).filter(models.AppUser.email.in_(missing_ids)).all()
             for au in app_users:
                 user_map[au.email] = au.full_name

        print(f"🔍 [get_user_map] Requested: {len(user_ids)}, Found: {len(user_map)}")
        return user_map
    except Exception as e:
        print(f"❌ [get_user_map] Error: {e}")
        return {}
    finally:
        db.close()

@app.get("/projects/{project_id}/members")
def get_project_members(project_id: str):
    """Get all members associated with this project's organization/team"""
    db = database.SessionCore()
    try:
        # 1. Get Project
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project: return []
        
        users_in_org = []
        
        # 2a. Try Organization ID
        # 2a. Try Organization ID
        if project.organization_id:
            try:
                # Use AccountUser joined with OrganizationUser
                # models.User was mapping to AppUser which has no organization_id
                users_in_org = db.query(models.AccountUser).join(
                    models.OrganizationUser, 
                    models.AccountUser.id == models.OrganizationUser.user_id
                ).filter(
                    models.OrganizationUser.organization_id == project.organization_id
                ).all()
                print(f"✅ [get_project_members] Found {len(users_in_org)} users in Org {project.organization_id}")
            except Exception as e:
                print(f"❌ [get_project_members] Error fetching org users: {e}")
                users_in_org = []
        else:
            print(f"⚠️ [get_project_members] Project {project_id} has no organization_id. Checking if current user connects...")
            # Fallback: If no org, at least show the creator or owner?
            # For now, empty list is fine, but we might want to inject "admin" or current user if needed.
            if project.team_id:
                 # TODO: Fetch team members
                 pass
            
        # 2b. Fallback/Supplement: Check Assigned Collaborators (JSON)
        # assigned_collaborators is { "id": %, ... }
        collab_users = []
        if project.assigned_collaborators:
            collab_ids = list(project.assigned_collaborators.keys())
            if collab_ids:
                # Query Collaborators table (resources_collaborators)
                # Note: These might not be in AppUser table, or might be linked.
                # Ideally check both User and Collaborator tables.
                collab_records = db.query(models.Collaborator).filter(models.Collaborator.id.in_(collab_ids)).all()
                collab_users = [
                    {"id": c.id, "name": c.name, "email": c.email, "role": c.role} 
                    for c in collab_records
                ]

        # Combine results
        # Only include AppUsers (users_in_org) if they are not already in collab_users to avoid duplications?
        # Actually, prioritize AppUsers as they can login.
        
        final_members = []
        seen_ids = set()
        
        # Add Org Users first
        # Add Org Users first
        for u in users_in_org:
            if u.id not in seen_ids:
                final_members.append({
                    "id": u.id, 
                    "name": u.full_name, # AccountUser has full_name
                    "email": u.email, 
                    "role": getattr(u, 'role', 'Member')
                })
                seen_ids.add(u.id)
                
        # Add Collaborators next
        for c in collab_users:
            if c["id"] not in seen_ids:
                final_members.append(c)
                seen_ids.add(c["id"])
                
        return final_members
    except Exception as e:
        print(f"Error fetching members: {e}")
        return []
    finally:
        db.close()

@app.get("/tasks/{task_id}")
def get_task_details(task_id: str):
    import datetime
    db = database.SessionOps()
    try:
        task = db.query(DailyTask).filter(DailyTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        # Get Comments
        comments = db.query(DailyComment).filter(DailyComment.task_id == task_id).order_by(DailyComment.created_at.desc()).all()
        
        # BATCH FETCH AUTHORS
        # Collect all non-null user_ids
        user_ids = list(set([c.user_id for c in comments if c.user_id]))
        
        # Query Core DB
        user_map = {}
        if user_ids:
             user_map = get_user_map(user_ids)
             
        # Check for missing users
        for uid in user_ids:
             if uid not in user_map:
                  # print(f"⚠️ [get_task_details] User not found: {uid}")
                  pass
        
        formatted_comments = []
        for c in comments:
            # Resolve Author
            # Fallback logic: 
            # 1. If user_id exists -> Try Map -> Fallback "Unknown User"
            # 2. If guest -> Use stored name or "Guest"
            
            display_name = "Guest"
            author_type = "guest"
            avatar_url = None
            
            if c.user_id:
                 author_type = "user"
                 display_name = user_map.get(c.user_id, "Unknown User")
            else:
                 author_type = "guest"
                 display_name = c.user_name or "Guest"

            # UTC ISO for Frontend
            created_iso = c.created_at.isoformat() if c.created_at else None
            # If created_at is naive, assume UTC (since we are moving to that)
            if c.created_at: 
                 if c.created_at.tzinfo is None:
                     created_iso = c.created_at.replace(tzinfo=datetime.timezone.utc).isoformat()
                 else:
                     created_iso = c.created_at.astimezone(datetime.timezone.utc).isoformat()

            formatted_comments.append({
                "id": c.id,
                "content": c.content,
                "createdAt": created_iso,
                "author": {
                     "id": c.user_id,
                     "type": author_type,
                     "displayName": display_name,
                     "avatarUrl": avatar_url 
                }
            })
        
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "assignees": task.assignees or [],
            "attachments": task.attachments or [],
            "comments": formatted_comments
        }
    finally:
        db.close()

@app.post("/tasks/{task_id}/attachments")
async def upload_task_attachment(
    task_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    import shutil
    import os
    
    db = database.SessionOps()
    try:
        task = db.query(DailyTask).filter(DailyTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        # Save File
        # Ensure absolute path to avoid CWD issues
        abs_static = os.path.abspath(STATIC_DIR)
        UPLOAD_DIR = os.path.join(abs_static, "uploads")
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        file_id = str(uuid.uuid4())
        ext = file.filename.split('.')[-1]
        safe_name = f"{file_id}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        new_attachment = {
            "name": file.filename,
            "url": f"/static/uploads/{safe_name}",
            "type": file.content_type,
            "uploaded_by": user_id,
            "uploaded_at": str(datetime.datetime.now())
        }
        
        # Update Task Attachments
        current_attachments = task.attachments or []
        # Ensure it's a list (sometimes JSON defaults behave oddly in different DBs)
        if not isinstance(current_attachments, list):
            current_attachments = []
            
        current_attachments.append(new_attachment)
        
        # Re-assign to force detection of change
        task.attachments = list(current_attachments) 
        db.add(task) # Ensure dirty state
        db.commit()
        
        return new_attachment
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

def get_project_channels_safe(project_id: str):
    import types
    db = database.SessionOps()
    try:
        channels = db.query(DailyChannel).filter(DailyChannel.project_id == project_id).all()
        # If no channels, create default 'general'
        if not channels:
            gen = DailyChannel(id=str(uuid.uuid4()), project_id=project_id, name="general", type="text")
            db.add(gen)
            db.commit()
            channels = [gen]
            
        return [types.SimpleNamespace(id=c.id, name=c.name, type=c.type) for c in channels]
    finally:
        db.close()

def create_channel_safe(project_id: str, name: str, type: str = "text"):
    import types
    db = database.SessionOps()
    try:
        new_id = str(uuid.uuid4())
        chan = DailyChannel(id=new_id, project_id=project_id, name=name, type=type)
        db.add(chan)
        db.commit()
        return types.SimpleNamespace(id=chan.id, name=chan.name, type=chan.type)
    finally:
        db.close()

def get_channel_messages_safe(channel_id: str, limit: int = 50):
    import types
    db = database.SessionOps()
    try:
        # Fetch with attachments and threading info
        # Order by created_at DESC for pagination, then flip
        msgs = db.query(DailyMessage).filter(DailyMessage.channel_id == channel_id).order_by(DailyMessage.created_at.desc()).limit(limit).all()
        
        result = []
        for m in msgs:
            result.append({
                "id": m.id,
                "sender_id": m.sender_id,
                "content": m.content,
                "attachments": m.attachments or [],
                "parent_id": m.parent_id,
                "created_at": m.created_at.isoformat() if m.created_at else None
            })
        return result[::-1]
    finally:
        db.close()

def create_message_safe(channel_id: str, user_id: str, content: str, parent_id: int = None, attachments: list = None):
    db = database.SessionOps()
    try:
        msg = DailyMessage(
            channel_id=channel_id,
            sender_id=user_id,
            content=content,
            parent_id=parent_id,
            attachments=attachments or []
        )
        db.add(msg)
        db.commit()
        return {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "attachments": msg.attachments,
            "parent_id": msg.parent_id,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        }
    finally:
        db.close()

@app.get("/projects/{project_id}/channels")
def get_channels(project_id: str):
    return get_project_channels_safe(project_id)

@app.post("/projects/{project_id}/channels")
def create_channel(project_id: str, name: str = Body(..., embed=True), type: str = Body("text", embed=True)):
    return create_channel_safe(project_id, name, type)

@app.get("/channels/{channel_id}/messages")
def get_messages(channel_id: str):
    return get_channel_messages_safe(channel_id)

@app.post("/channels/{channel_id}/messages")
def post_message(
    channel_id: str, 
    content: str = Body(None), 
    parent_id: int = Body(None),
    attachments: list = Body(None), # [{name, url, type}]
    user_id: str = Depends(get_current_user_id) # Uses header X-User-ID
):
    if not content and not attachments:
        raise HTTPException(status_code=400, detail="Message must have content or attachments")
    return create_message_safe(channel_id, user_id, content, parent_id, attachments)

# Legacy Chat (Redirect to/Bridge to #general if possible, or just keep working as project-level for legacy)
# For now, let's leave legacy alone or deprecate it. The new UI will use new endpoints.
# If I remove the old one, the old UI breaks immediately before I deploy the new one.
# So I will keep the old one BUT making it use 'general' channel would be smart.
# But for safety, I'll just add NEW specific endpoints above.

# FILE UPLOAD (Simple Static)
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    import shutil
    import os
    
    # Save to static/uploads
    UPLOAD_DIR = "backend/services/daily/static/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    ext = file.filename.split('.')[-1]
    safe_name = f"{file_id}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "url": f"/static/uploads/{safe_name}",
        "name": file.filename,
        "type": file.content_type,
        "size": 0 # TODO: Calculate size
    }


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
        
    response = FileResponse(index_path)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

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
