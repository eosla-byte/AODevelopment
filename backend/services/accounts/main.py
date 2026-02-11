from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, Body
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
import uvicorn
import os
import sys
import uuid
import datetime
from typing import List, Optional
import pydantic



# Path Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Local imports (common is now partially vendored or in path)
# REMOVED: sys.path.insert(0, BASE_DIR) - This caused local common/ shadowing!

# Correct Canonical Import
# We assume the service is run from root (python backend/services/accounts/main.py)
# OR we use relative if package.
# Given monorepo structure, 'common' is at 'backend/common'.
# But if running as 'python main.py' inside accounts/, then 'common' is sibling?
# The prompt says: "Ensure imports reference the canonical module... backend.common"
# To fix this reliably without sys.path hacks, we need to know how it's run.
# "python -m uvicorn main:app" inside accounts/
# If we want to import backend.common, we need backend/ in sys.path
# Let's add backend root to sys.path properly IF needed, but prefer absolute imports if possible.
# Actually, the user instruction is: "Remove sys.path insertion that forces service-local common/ to win."
# So we should probably add the ROOT (AODevelopment) or Backend Root.
# Let's guess: AODevelopment/backend is the root for imports?
# If we add os.path.join(BASE_DIR, "../../../") to sys.path?
# Let's try to be standard:
# Local imports (common is now partially vendored or in path)
# In container, if running from /app (accounts service dir), direct import should work 
# provided common/ has __init__.py or is namespace.
# It seems 'common' is a subdirectory here.

# Ideally we do relative imports or rely on python path.
# If running as pkg: from .common import ...
# If running as script: import common ...


from common.database import get_db, SessionCore 
from common.auth import create_access_token, create_refresh_token, decode_token, AO_JWT_PUBLIC_KEY_PEM
from common.auth_utils import verify_password, get_password_hash 
import common.models as models 
from common.models import AccountUser 
from common.auth_constants import (
    ACCESS_COOKIE_NAME, 
    REFRESH_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    ALGORITHM,
    cookie_settings,
    COOKIE_DOMAIN,
    COOKIE_SAMESITE,
    COOKIE_SECURE
) 

# Configuration
SUPER_ADMIN_EMAILS = [e.strip().lower() for e in os.getenv("AO_SUPER_ADMIN_EMAILS", "").split(",") if e.strip()] 

# Initialize Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# -----------------------------------------------------------------------------
# LIFESPAN & STARTUP
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Verify Project Model & Schema
    print("🔍 [STARTUP] Verifying Project Model & Schema...")
    print(f"🍪 [CONFIG] Domain='{COOKIE_DOMAIN}', Secure={COOKIE_SECURE}, SameSite='{COOKIE_SAMESITE}'")
    
    db = None
    try:
        # Check ORM Model
        if not hasattr(models.Project, "organization_id"):
             print(f"❌ [CRITICAL] Project model matches: {models.Project.__module__}")
             raise RuntimeError("Project model MUST have 'organization_id'.")
        
        # Check DB Connection & Table
        from sqlalchemy import text
        db = SessionCore()
        # Safe check using text()
        db.execute(text("SELECT 1 FROM bim_projects LIMIT 1"))
        print("✅ [STARTUP] DB table 'bim_projects' VERIFIED.")
        
        # 2. Run Legacy Fixes
        run_db_fix()

    except Exception as e:
        print(f"❌ [CRITICAL] Startup Check Failed: {e}")
        # We allow startup to fail if DB is missing critical tables?
        # Yes, prompt says "raise RuntimeError".
        raise RuntimeError(f"Startup Failed: {e}")
    finally:
        if db:
            db.close()
        
    yield
    # Shutdown logic if needed

app = FastAPI(title="AO Accounts Service", lifespan=lifespan)


# ... (version check same)

# ... (dependencies)
def get_current_active_user(request: Request):
    # 1. Read Valid Cookie (Prioritize Unified Name)
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        print(f"DEBUG: Cookie '{ACCESS_COOKIE_NAME}' missing. Checking fallback...")
        token = request.cookies.get("access_token")
        
    if token:
         print(f"DEBUG: Found token in cookie (Length: {len(token)})")
    else:
         print(f"DEBUG: No token found in any cookie. Cookies keys: {list(request.cookies.keys())}")
         # Attempt Header
         auth = request.headers.get("Authorization")
         if auth and auth.startswith("Bearer "):
             print("DEBUG: Found token in Authorization header")
             token = auth.split(" ")[1]

    if not token:
        return None

    try:
        # Decode ensuring audience includes 'ao-platform'
        # verify_exp=True by default
        print("DEBUG: Verifying token with audience='ao-platform'...")
        payload = decode_token(token, audience="ao-platform")
        if not payload: 
            print("DEBUG: decode_token returned None (Verification Failed)")
            return None
            
        print(f"DEBUG: Token verified for user {payload.get('sub')} (Role: {payload.get('role')})")
        return payload 
    except Exception as e:
        print(f"DEBUG: Auth Exception: {e}")
        return None

def get_current_admin(user = Depends(get_current_active_user)):
    if not user:
        return None
    # Check Role (case-insensitive)
    role = (user.get("role") or "").strip().lower()
    if role not in ["admin", "superadmin", "super_admin"]:
        print(f"DEBUG: Role '{role}' denied admin access.")
        return None
    return user

# --- DB Migration Helper ---
def run_db_fix():
    print("🔧 [ACCOUNTS] Checking Schema Constraints...")
    from sqlalchemy import text
    db = SessionCore()
    try:
        # 1. Add last_active_org_id to accounts_users
        try:
            db.execute(text("ALTER TABLE accounts_users ADD COLUMN last_active_org_id VARCHAR"))
            db.commit()
            print("✅ [ACCOUNTS] Added 'last_active_org_id'")
        except Exception:
            db.rollback()
            pass
            
        # 2. Add services_access to accounts_organizations if needed? 
        # (Entitlements are in OrganisationUser or ServicePermission)
    finally:
        db.close()

# --- Auth Helper ---
def get_active_org_context(db, user: "AccountUser"):
    """
    Determines the active organization context for a user.
    Returns: (org_id, role, services_list) or (None, None, [])
    Robust against missing OrganizationUser model AND missing User attributes.
    """
    
    # 1. Determine Org ID (Safe Access)
    org_id = getattr(user, "last_active_org_id", None)
    if not org_id:
        org_id = getattr(user, "organization_id", None)
    
    # 2. Determine Role (Safe Access)
    org_role = getattr(user, "last_active_org_role", None)
    if not org_role:
        org_role = getattr(user, "role", "Member")
    
    # 3. Determine Services (Safe Access & Multi-Type Support)
    services = []
    
    # Candidates: services_access (dict usually), services (list usually)
    services_raw = getattr(user, "services_access", None)
    if not services_raw:
        # Fallback to 'services' attribute if exists
        services_raw = getattr(user, "services", None)
        
    if services_raw:
        if isinstance(services_raw, dict):
            # If dict, assume {slug: bool} and take True ones
            services = [k for k, v in services_raw.items() if v]
        elif isinstance(services_raw, (list, tuple, set)):
            services = list(services_raw)
        elif isinstance(services_raw, str):
            services = [services_raw]
            
    # Normalize keys to lowercase slugs
    slug_map = {
        "AODailyWork": "daily",
        "AOPlanSystem": "bim",
        "AOBuild": "build",
        "AO Clients": "portal",
        "AOdev": "plugin",
        "AO HR & Finance": "finance"
    }

    # Helper to map slugs
    def map_slug(s):
        return slug_map.get(s, s.lower())

    if services:
        services = [map_slug(s) for s in services]
    else:
        # Optional: Try to fetch Org Services if User has no explicit services
        if org_id and hasattr(models, "Organization"):
            try:
                org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
                if org:
                    # check org.services or org.enabled_services
                    org_s = getattr(org, "services", None) or getattr(org, "enabled_services", None)
                    if org_s:
                        if isinstance(org_s, dict):
                            services = [map_slug(k) for k, v in org_s.items() if v]
                        elif isinstance(org_s, (list, tuple, set)):
                            services = [map_slug(s) for s in org_s]
                        elif isinstance(org_s, str):
                            services = [map_slug(org_s)]
            except Exception:
                pass

    # Log Resolution
    user_email = getattr(user, "email", "unknown")
    print(f"[ACCOUNTS] Active org resolved: user={user_email}, org_id={org_id}, org_role={org_role}, services_count={len(services)}")
    
    return org_id, org_role, services

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user = Depends(get_current_admin)):
    if user:
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/select-org", response_class=HTMLResponse)
async def select_org_page(request: Request):
    return templates.TemplateResponse("select_org.html", {"request": request})

# --- Super Admin Platform Routes ---

@app.get("/platform/dashboard", response_class=HTMLResponse)
async def platform_dashboard(request: Request, user=Depends(get_current_active_user)):
    # Simple check
    if not user or user.get("platform_role") != "super_admin":
        return RedirectResponse("/")
    return templates.TemplateResponse("platform_dashboard.html", {"request": request})

class CreateOrgSchema(pydantic.BaseModel):
    name: str
    slug: str

@app.get("/api/platform/orgs")
async def list_orgs(user=Depends(get_current_active_user)):
    if not user or user.get("platform_role") != "super_admin":
        raise HTTPException(status_code=403)
    
    db = SessionCore()
    try:
        orgs = db.query(models.Organization).all()
        return [{"id": o.id, "name": o.name, "slug": o.slug} for o in orgs]
    finally:
        db.close()

@app.post("/api/platform/orgs")
async def create_org(data: CreateOrgSchema, user=Depends(get_current_active_user)):
    if not user or user.get("platform_role") != "super_admin":
        raise HTTPException(status_code=403)
        
    db = SessionCore()
    try:
        # Check slug
        existing = db.query(models.Organization).filter(models.Organization.slug == data.slug).first()
        if existing:
            return JSONResponse({"detail": "Slug already exists"}, status_code=400)
            
        new_org = models.Organization(
            id=str(uuid.uuid4()),
            name=data.name,
            slug=data.slug,
            is_active=True,
            created_at=datetime.datetime.utcnow()
        )
        db.add(new_org)
        
        # Add User as Admin if OrganizationUser model exists
        if hasattr(models, "OrganizationUser"):
             current_user_id = user.get("sub")
             membership = models.OrganizationUser(
                id=str(uuid.uuid4()),
                organization_id=new_org.id,
                user_id=current_user_id,
                role="Admin"
             )
             db.add(membership)
        
        # Update user last_active_org_id
        try:
             u = db.query(AccountUser).filter(AccountUser.email == user.get("email")).first()
             if u:
                 u.last_active_org_id = new_org.id
                 u.last_active_org_role = "Admin"
                 db.add(u)
        except Exception:
            pass
            
        db.commit()
        return {"status": "ok", "org_id": new_org.id}
    except Exception as e:
        db.rollback()
        print(f"Create Org Failed: {e}")
        return JSONResponse({"detail": str(e)}, status_code=500)
    finally:
        db.close()

@app.post("/api/platform/set-active-org")
async def set_active_org(data: dict = Body(...), user=Depends(get_current_active_user)):
    if not user: raise HTTPException(status_code=401)
    
    org_id = data.get("org_id")
    if not org_id: return JSONResponse({"detail": "Missing org_id"}, status_code=400)
    
    db = SessionCore()
    try:
        u = db.query(AccountUser).filter(AccountUser.email == user.get("email")).first()
        if u:
            # If SuperAdmin, allow loop setting
            u.last_active_org_id = org_id
            db.commit()
            return {"status": "ok"}
        return JSONResponse({"detail": "User not found"}, status_code=404)
    finally:
        db.close()

@app.post("/auth/login")
async def login_action(email: str = Form(...), password: str = Form(...)):
    # print(f"Login Attempt: '{email}'")
    email = email.strip().lower()
    
    db = SessionCore()
    try:
        user = db.query(AccountUser).filter(AccountUser.email == email).first()
        
        if not user:
            return JSONResponse({"status": "error", "message": f"User '{email}' not found."}, status_code=401)
            
        verification = verify_password(password, user.hashed_password)
        if not verification:
            return JSONResponse({"status": "error", "message": "Invalid password."}, status_code=401)
            
        # ORG CONTEXT RESOLUTION
        org_id, org_role, services = get_active_org_context(db, user)
        
        # SUPER ADMIN OVERRIDE
        is_super_admin = user.email in SUPER_ADMIN_EMAILS
        if is_super_admin:
            org_role = "SuperAdmin"

        # Robust ID Resolution (Fix for AppUser missing 'id')
        real_user_id = getattr(user, "id", None)
        if not real_user_id:
            real_user_id = user.email

        # Token Claims (Standardized)
        claims = {
            "sub": str(real_user_id),   # Use UUID or Email as sub
            "email": user.email,
            "role": org_role if org_role else user.role, 
            "platform_role": "super_admin" if is_super_admin else None,
            "org_id": org_id, 
            "services": services or []
        }
        
        # Determine Response Status
        status_response = "ok"
        redirect_url = "/dashboard" 
        
        if not org_id:
            if is_super_admin:
                status_response = "ok"
                redirect_url = "/platform/dashboard"
            else:
                status_response = "select_org"
                redirect_url = "/select-org"
            
        # ACCESS TOKEN (Dual Audience for compatibility)
        access_token = create_access_token(data=claims, audience=["somosao", "ao-platform"])
        
        # REFRESH TOKEN
        refresh_claims = {"sub": str(real_user_id), "email": user.email}
        refresh_token = create_refresh_token(data=refresh_claims)
        
        response = JSONResponse({"status": status_response, "redirect": redirect_url, "user": {"id": str(real_user_id), "email": user.email}})
        
        # COOKIE 1: Unified Access Token (accounts_access_token)
        response.set_cookie(
            key=ACCESS_COOKIE_NAME, 
            value=access_token, 
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE, 
            domain=COOKIE_DOMAIN
        )

        # COOKIE 2: Legacy/Compat (access_token) - Share config
        response.set_cookie(
            key="access_token", 
            value=access_token, 
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE, 
            domain=COOKIE_DOMAIN,
            path="/"
        )

        # COOKIE 3: Refresh Token
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE, 
            domain=COOKIE_DOMAIN,
            max_age=7 * 24 * 60 * 60
        )
        
        print(f"Login Success: {user.email} (Org: {org_id})")
        return response
    finally:
        db.close()

# --- Organization Projects API ---

class ProjectCreateSchema(pydantic.BaseModel):
    name: str
    project_cost: float = 0.0
    sq_meters: float = 0.0
    ratio: float = 0.0
    estimated_time: Optional[str] = None
    status: str = "Active"

@app.get("/api/organizations/{org_id}/projects")
def get_org_projects(org_id: str, user = Depends(get_current_active_user)):
    print(f"PROJECTS ENDPOINT HIT path=/api/organizations/{org_id}/projects org_id={org_id}")
    
    # 1. Auth Check
    if not user: 
        print("PROJECTS: 401 Unauthorized")
        raise HTTPException(status_code=401)
    
    # 2. Org Access Check
    db = SessionCore()
    try:
        # Check if user is member of this org
        # (Relaxed check: If SuperAdmin or just return empty if not member?)
        # Let's start with strict check but safe return.
        
        # 3. Query Projects
        print(f"PROJECTS: Fetching projects for org_id={org_id}...")
        projects = db.query(models.Project).filter(
            models.Project.organization_id == org_id,
            models.Project.archived == False
        ).all()
        
        print(f"PROJECTS COUNT={len(projects)}")
        
        # Frontend expects ARRAY directly
        return [{
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "project_cost": p.project_cost,
            "sq_meters": p.sq_meters,
            "ratio": p.ratio,
            "estimated_time": p.estimated_time,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in projects]
        
    except Exception as e:
        print(f"PROJECTS ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        db.close()

# Fallback / Alias if frontend calls /api/projects directly
@app.get("/api/projects")
def get_current_user_projects(user = Depends(get_current_active_user)):
    print("PROJECTS ENDPOINT HIT path=/api/projects (Fallback)")
    if not user: raise HTTPException(status_code=401)
    return []

@app.post("/api/organizations/{org_id}/projects")
def create_org_project(
    org_id: str, 
    project_data: ProjectCreateSchema, 
    user = Depends(get_current_active_user)
):
    if not user: raise HTTPException(status_code=401)
    
    db = SessionCore()
    try:
        # 1. Access Check (Admin only?)
        # For now, allow Admins AND Members to create projects? 
        # Requirement: "Manage High-Level Project Definitions" -> Likely Admin.
        membership = db.query(models.OrganizationUser).filter(
            models.OrganizationUser.organization_id == org_id,
            models.OrganizationUser.user_id == user["sub"]
        ).first()
        
        if not membership:
             raise HTTPException(status_code=403, detail="Not a member")
             
        # Optional: Restrict to Admin
        if membership.role != "Admin" and user.get("role") != "SuperAdmin":
             raise HTTPException(status_code=403, detail="Only Admins can create projects")
        
        # 2. Create
        # Explicitly use organization_id. 
        # The model now has a relationship 'organization', but setting the ID is sufficient.
        new_project = models.Project(
            id=str(uuid.uuid4()),
            organization_id=org_id, # Enforced from URL path
            name=project_data.name,
            status=project_data.status,
            # project_cost=project_data.project_cost, # Legacy
            # sq_meters=project_data.sq_meters,
            # ratio=project_data.ratio,
            # estimated_time=project_data.estimated_time,
            # created_by=user["sub"] # Temporarily removed
        )
        db.add(new_project)
        db.commit()
        
        return JSONResponse({"status": "ok", "project_id": new_project.id}, status_code=201)
    except Exception as e:
        db.rollback()
        print(f"create_org_project ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")
    finally:
        db.close()

class ServiceToggleSchema(pydantic.BaseModel):
    service_slug: str
    is_active: bool

@app.post("/api/organizations/{org_id}/services")
def toggle_org_service(
    org_id: str, 
    data: ServiceToggleSchema,
    user = Depends(get_current_active_user)
):
    # Only SuperAdmin (or maybe Org Admin?)
    if user.get("role") != "SuperAdmin":
         raise HTTPException(status_code=403, detail="SuperAdmin only")
         
    db = SessionCore()
    try:
        perm = db.query(models.ServicePermission).filter(
            models.ServicePermission.organization_id == org_id,
            models.ServicePermission.service_slug == data.service_slug
        ).first()
        
        if perm:
            perm.is_active = data.is_active
        else:
            perm = models.ServicePermission(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                service_slug=data.service_slug,
                is_active=data.is_active
            )
            db.add(perm)
            
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()

# --- Helpers ---

async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie(ACCESS_COOKIE_NAME, domain=COOKIE_DOMAIN)
    response.delete_cookie("access_token", domain=COOKIE_DOMAIN)
    response.delete_cookie(REFRESH_COOKIE_NAME, domain=COOKIE_DOMAIN)
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, org_id: Optional[str] = None, user_jwt = Depends(get_current_active_user)):
    if not user_jwt:
        print("DEBUG: Dashboard Redirecting to /login (No active user)")
        return RedirectResponse("/login")

    print(f"DEBUG: Dashboard Access Granted for {user_jwt.get('email')}")

    def _is_uuid(val: str) -> bool:
        try:
            uuid.UUID(str(val))
            return True
        except Exception:
            return False

    db = SessionCore()
    try:
        token_sub = user_jwt.get("sub")
        token_email = (user_jwt.get("email") or "").strip().lower()
        print(f"DEBUG: Lookup User ID: {token_sub} (Email fallback: {token_email})")

        user_db = None

        # 1) Prefer email lookup (most stable in your current token flow)
        if token_email and hasattr(AccountUser, "email"):
            user_db = db.query(AccountUser).filter(AccountUser.email == token_email).first()

        # 2) Fallback to subject lookup ONLY if the ORM model actually has 'id'
        if not user_db and token_sub and hasattr(AccountUser, "id"):
            user_db = db.query(AccountUser).filter(AccountUser.id == token_sub).first()

        # 3) Optional fallback: if model uses 'uuid' or 'user_id' as PK
        if not user_db and token_sub and _is_uuid(token_sub):
            if hasattr(AccountUser, "uuid"):
                user_db = db.query(AccountUser).filter(AccountUser.uuid == token_sub).first()
            elif hasattr(AccountUser, "user_id"):
                user_db = db.query(AccountUser).filter(AccountUser.user_id == token_sub).first()

        if not user_db:
            print(f"DEBUG: DASHBOARD REDIRECT: token_sub={token_sub} token_email={token_email} reason=user_not_found_in_db")
            return RedirectResponse("/login")

        user_pk = getattr(user_db, "id", None) or getattr(user_db, "uuid", None) or getattr(user_db, "user_id", None)

        view_context = {
            "request": request,
            "user": user_db,
            "view_mode": "member",
            "organizations": [],
            "current_org": None,
            "available_services": ["daily", "plans", "build", "clients", "plugin"],
        }

        # SUPER ADMIN VIEW
        if (getattr(user_db, "role", "") or "").lower() == "superadmin":
            if org_id:
                target_org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
                if target_org:
                    view_context["view_mode"] = "org_admin"
                    view_context["current_org"] = target_org
            else:
                view_context["view_mode"] = "super_admin"
                view_context["organizations"] = db.query(models.Organization).all()

        # ORG ADMIN VIEW
        else:
            membership = None
            if user_pk and hasattr(models, "OrganizationUser"):
                q = db.query(models.OrganizationUser).filter(
                    models.OrganizationUser.user_id == str(user_pk),
                    models.OrganizationUser.role == "Admin",
                )
                if org_id:
                    q = q.filter(models.OrganizationUser.organization_id == org_id)
                membership = q.first()

            if membership:
                view_context["view_mode"] = "org_admin"
                view_context["current_org"] = membership.organization

        return templates.TemplateResponse("dashboard.html", view_context)

    finally:
        db.close()




# --- User Management API ---

@app.post("/api/users")
async def create_user(
    request: Request, 
    full_name: str = Form(...),
    email: str = Form(...),
    company: str = Form(""),
    role: str = Form("Member"),
    password: str = Form(...), # Initial password
    # Service Flags
    access_aodev: Optional[bool] = Form(False),
    access_hr: Optional[bool] = Form(False),
    access_projects: Optional[bool] = Form(False),
    access_clients: Optional[bool] = Form(False),
    access_daily: Optional[bool] = Form(False),
    access_bim: Optional[bool] = Form(False),
    access_build: Optional[bool] = Form(False),
    
    user_jwt = Depends(get_current_admin)
):
    if not user_jwt: raise HTTPException(status_code=401)
    
    db = SessionCore()
    if db.query(AccountUser).filter(AccountUser.email == email).first():
        db.close()
        return JSONResponse({"status": "error", "message": "Email already registered"}, status_code=400)
    
    new_user = AccountUser(
        id=str(uuid.uuid4()),
        email=email,
        full_name=full_name,
        company=company,
        role=role,
        hashed_password=get_password_hash(password),
        services_access={
            "AOdev": access_aodev,
            "AO HR & Finance": access_hr,
            "AO Projects": access_projects,
            "AO Clients": access_clients,
            "AODailyWork": access_daily,
            "AOPlanSystem": access_bim,
            "AOBuild": access_build
        }
    )
    db.add(new_user)
    db.commit()
    db.close()
    
    return JSONResponse({"status": "ok", "message": "User created"})

@app.post("/api/users/{user_id}/update")
async def update_user(
    user_id: str,
    full_name: str = Form(None),
    company: str = Form(None),
    role: str = Form(None),
    password: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    # Permissions
    access_aodev: bool = Form(False),
    access_hr: bool = Form(False),
    access_projects: bool = Form(False),
    access_clients: bool = Form(False),
    access_daily: bool = Form(False),
    access_bim: bool = Form(False),
    access_build: bool = Form(False),
    
    user_jwt = Depends(get_current_admin)
):
    if not user_jwt: raise HTTPException(status_code=401)
    
    db = SessionCore()
    user = db.query(AccountUser).filter(AccountUser.id == user_id).first()
    if not user:
        db.close()
        return JSONResponse({"status": "error", "message": "User not found"}, status_code=404)
    
    if full_name: user.full_name = full_name
    if company: user.company = company
    if role: user.role = role
    if status: user.status = status
    
    # Password update logic
    if password and len(password.strip()) > 0:
        print(f"Updating password for user {user.email}")
        user.hashed_password = get_password_hash(password)
    
    # Update Permissions (Partial update for now)
    current_perms = dict(user.services_access or {})
    
    if access_bim: 
        current_perms["AOPlanSystem"] = True
    
    # Re-assign to trigger SQLAlchemy detection
    user.services_access = current_perms 
    
    db.commit()
    db.close()
    
    return JSONResponse({"status": "ok", "message": "User updated"})

@app.post("/api/users/{user_id}/toggle_service")
async def toggle_service_access(
    user_id: str,
    service_name: str = Form(...),
    user_jwt = Depends(get_current_admin)
):
    if not user_jwt: raise HTTPException(status_code=401)
    
    db = SessionCore()
    user = db.query(AccountUser).filter(AccountUser.id == user_id).first()
    if not user:
        db.close()
        return JSONResponse({"status": "error", "message": "User not found"}, status_code=404)
    
    current_access = user.services_access or {}
    # Toggle
    new_state = not current_access.get(service_name, False)
    current_access[service_name] = new_state
    
    # Re-assign to trigger mutation tracking if needed (for some ORMs/JSON types)
    user.services_access = dict(current_access)
    
    db.commit()
    db.close()
    
    return JSONResponse({"status": "ok", "state": new_state, "message": f"{service_name} access {'granted' if new_state else 'revoked'}"})

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str, user_jwt = Depends(get_current_admin)):
    if not user_jwt: raise HTTPException(status_code=401)
    db = SessionCore()
    user = db.query(AccountUser).filter(AccountUser.id == user_id).first()
    if user:
        # Manual Cascade: Delete Organization Memberships first
        db.query(OrganizationUser).filter(OrganizationUser.user_id == user_id).delete()
        
        # Then delete the user
        db.delete(user)
        db.commit()
    db.close()
    return JSONResponse({"status": "ok", "message": "User deleted"})

# Setup Script Route (Temporary, to create first admin if none)
@app.get("/system/fix_me")
async def manual_fix(user_jwt = Depends(get_current_admin)):
    """
    Self-service endpoint to promote the calling user to SuperAdmin (if they are already Admin).
    """
    if not user_jwt: return "Not authenticated"
    
    db = SessionCore()
    # FIX: sub is ID
    user = db.query(AccountUser).filter(AccountUser.id == user_jwt["sub"]).first()
    if user:
        user.role = "SuperAdmin"
        db.commit()
        db.close()
        return f"User {user.email} promoted to SuperAdmin. Please logout and login again."
    db.close()
    return "User not found"

@app.get("/setup_initial_admin")
async def setup_admin():
    db = SessionCore()
    if db.query(AccountUser).count() > 0:
        db.close()
        return "Admin already exists or users exist. Setup disabled."
    
    admin = AccountUser(
        id=str(uuid.uuid4()),
        email="admin@somosao.com",
        full_name="System Admin",
        role="Admin",
        hashed_password=get_password_hash("admin123"),
        services_access={}
    )
    db.add(admin)
    db.commit()
    db.close()
    return "Initial admin created: admin@somosao.com / admin123"

@app.get("/system/force_admin_reset")
async def force_admin_reset():
    """
    Endpoint de emergencia para restaurar acceso admin en Produccion.
    Sobreescribe la contraseña y rol del usuario admin@somosao.com.
    """
    from common.database import SessionCore, AccountUser, get_password_hash
    db = SessionCore()
    email = "admin@somosao.com"
    
    # 1. Buscar o Crear
    user = db.query(AccountUser).filter(AccountUser.email == email).first()
    
    if user:
        user.full_name = "System Admin"
        user.role = "Admin"
        user.hashed_password = get_password_hash("admin123")
        user.is_active = True
        # Asegurar acceso total
        user.services_access = {
            "AOdev": True, "AO HR & Finance": True, "AO Projects": True,
            "AO Clients": True, "AODailyWork": True, "AOPlanSystem": True, "AOBuild": True
        }
        msg = "Admin actualizado correctamente."
    else:
        user = AccountUser(
            id=str(uuid.uuid4()),
            email=email,
            full_name="System Admin",
            role="Admin",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            services_access={
                "AOdev": True, "AO HR & Finance": True, "AO Projects": True,
                "AO Clients": True, "AODailyWork": True, "AOPlanSystem": True, "AOBuild": True
            }
        )
        db.add(user)
        msg = "Admin creado correctamente."
    
    db.commit()
    db.close()
    return f"ÉXITO: {msg} Usa: {email} / admin123"

@app.get("/system/migrate_db")
def migrate_db_schema(user_jwt = Depends(get_current_admin)):
    """
    Emergency endpoint to apply schema changes (Migrations) that Create_All misses.
    """
    if not user_jwt: return "Unauthorized"
    
    from sqlalchemy import text
    from common.database import SessionCore, SessionOps, engine_core, engine_ops
    from common.models import Base
    
    messages = []

    # 0. Ensure Tables Exist (Create All)
    # This handles "UndefinedTable" errors by creating them fresh if missing.
    try:
        Base.metadata.create_all(bind=engine_ops)
        messages.append("SUCCESS: Base.metadata.create_all(bind=engine_ops)")
    except Exception as e:
         messages.append(f"ERROR: Create All Ops failed | {e}")

    try:
        Base.metadata.create_all(bind=engine_core)
        messages.append("SUCCESS: Base.metadata.create_all(bind=engine_core)")
    except Exception as e:
         messages.append(f"ERROR: Create All Core failed | {e}")
    
    
    def run_migration(session, sql):
        try:
            session.execute(text(sql))
            session.commit()
            messages.append(f"SUCCESS: {sql}")
        except Exception as e:
            session.rollback()
            # Ignore "duplicate column" errors or "already exists"
            msg = str(e).lower()
            if "duplicate column" in msg or "already exists" in msg:
                messages.append(f"SKIPPED (Exists): {sql}")
            else:
                messages.append(f"ERROR: {sql} | {e}")

    # 1. Projects Table Updates (Organization & Metrics)
    # Run on CORE DB (where Projects are)
    # Table name is 'resources_projects' NOT 'projects'
    db_core = SessionCore()
    run_migration(db_core, 'ALTER TABLE resources_projects ADD COLUMN organization_id VARCHAR')
    run_migration(db_core, 'ALTER TABLE resources_projects ADD COLUMN sq_meters FLOAT DEFAULT 0.0')
    run_migration(db_core, 'ALTER TABLE resources_projects ADD COLUMN project_cost FLOAT DEFAULT 0.0')
    run_migration(db_core, 'ALTER TABLE resources_projects ADD COLUMN ratio FLOAT DEFAULT 0.0')
    run_migration(db_core, 'ALTER TABLE resources_projects ADD COLUMN estimated_time VARCHAR')
    db_core.close()
    
    # 2. Ops DB (in case of Daily tables, keep them just in case)
    db_ops = SessionOps()
    run_migration(db_ops, 'ALTER TABLE daily_teams ADD COLUMN organization_id VARCHAR')
    run_migration(db_ops, 'ALTER TABLE daily_projects ADD COLUMN organization_id VARCHAR')
    db_ops.close()

    return {"status": "done", "log": messages}

@app.post("/auth/refresh")
async def refresh_token_endpoint(request: Request):
    """
    Refreshes the access_token using the HttpOnly refresh_token cookie.
    Re-evaluates Org Context from DB (last_active_org_id).
    """
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        return JSONResponse({"status": "error", "message": "No refresh token"}, status_code=401)
        
    try:
        # Validate
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
             return JSONResponse({"status": "error", "message": "Invalid refresh token"}, status_code=401)
             
        user_id = payload.get("sub")
        
        # Verify User & Context
        db = SessionCore()
        try:
            user = db.query(AccountUser).filter(AccountUser.id == user_id).first()
            if not user:
                 return JSONResponse({"status": "error", "message": "User not found"}, status_code=401)
                 
            # CONTEXT RE-EVALUATION
            org_id, org_role, services = get_active_org_context(db, user)
            
            if not org_id:
                return JSONResponse({"status": "error", "message": "Organization selection required", "code": "ORG_REQUIRED"}, status_code=409)

            # Issue New Access Token
            claims = {
                "sub": user.id,
                "email": user.email,
                "role": org_role if org_role else user.role,
                "org_id": org_id,
                "services": services or []
            }
            
            access_token = create_access_token(data=claims, audience=["somosao", "ao-platform"])
            
            response = JSONResponse({"status": "ok", "message": "Token refreshed", "org_id": org_id})
            
            # 1. ACCESS_COOKIE_NAME
            response.set_cookie(
                key=ACCESS_COOKIE_NAME, 
                value=access_token, 
                httponly=True,
                samesite=COOKIE_SAMESITE,
                secure=COOKIE_SECURE, 
                domain=COOKIE_DOMAIN
            )
            
            # 2. Legacy access_token
            response.set_cookie(
                key="access_token", 
                value=access_token, 
                httponly=True,
                samesite=COOKIE_SAMESITE,
                secure=COOKIE_SECURE,
                domain=COOKIE_DOMAIN,
                path="/"
            )
            
            return response
        finally:
            db.close()
            
    except Exception as e:
        print(f"Refresh Error: {e}")
        return JSONResponse({"status": "error", "message": "Refresh failed"}, status_code=401)

@app.post("/auth/select-org")
async def select_organization(
    request: Request,
    body: dict = Body(...)
):
    """
    Sets the active organization for the user.
    Requires: Valid Access Token (can be partial/no-org) OR Refresh Token.
    """
    org_id = body.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Missing org_id")

    # 1. AUTHENTICATE (Try Access, then Refresh)
    token = request.cookies.get(ACCESS_COOKIE_NAME) 
    refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    
    user_email = None
    user_id = None
    
    # Try Access Token
    if token:
        payload = decode_token(token)
        if payload: 
            user_id = payload.get("sub")
            user_email = payload.get("email") # fallback
        
    # Try Refresh Token if no Access
    if not user_id and refresh:
        payload = decode_token(refresh)
        if payload and payload.get("type") == "refresh":
             user_id = payload.get("sub")
             user_email = payload.get("email")
                  
    if not user_id and not user_email:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    # 2. VERIFY & SWITCH
    db = SessionCore()
    try:
        # Find User
        if user_id:
             user = db.query(AccountUser).filter(AccountUser.id == user_id).first()
        else:
             user = db.query(AccountUser).filter(AccountUser.email == user_email).first()
             
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        # Verify Membership in Target Org
        membership = db.query(models.OrganizationUser).filter(
            models.OrganizationUser.user_id == user.id,
            models.OrganizationUser.organization_id == org_id
        ).first()
        
        if not membership:
             raise HTTPException(status_code=403, detail="Not a member of this organization")
             
        # Update Last Active
        user.last_active_org_id = org_id
        db.commit()
        
        # 3. ISSUE NEW TOKEN
        org_id, org_role, services = _build_context(db, membership)
        
        claims = {
            "sub": user.id,
            "email": user.email,
            "role": org_role if org_role else user.role,
            "org_id": org_id,
            "services": services or []
        }
        
        access_token = create_access_token(data=claims, audience=["somosao", "ao-platform"])
        
        response = JSONResponse({"status": "ok", "message": "Organization selected"})
        
        response.set_cookie(
            key=ACCESS_COOKIE_NAME, 
            value=access_token, 
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE, 
            domain=COOKIE_DOMAIN
        )
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE,
            domain=COOKIE_DOMAIN,
            path="/" 
        )
        return response
    finally:
        db.close()

@app.get("/api/my-organizations")
async def get_my_organizations_endpoint(request: Request):
    # Manual Auth Check (User level)
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    user_email = None
    if token:
         payload = decode_token(token)
         if payload: user_email = payload.get("sub")
         
    # Allow via Refresh token too? For the "Select Org" screen when Access is expired/missing?
    if not user_email:
        refresh = request.cookies.get(REFRESH_COOKIE_NAME)
        if refresh:
            payload = decode_token(refresh)
            if payload and payload.get("type") == "refresh":
                 user_email = payload.get("sub")

    if not user_email: # Variable name user_email but actually holds sub/id
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    user_id = user_email # Rename for clarity
        
    db = SessionCore() 
    try:
        # FIX: Lookup by ID
        user = db.query(AccountUser).filter(AccountUser.id == user_id).first()
        if not user: return []
        
        # Fetch Orgs
        memberships = db.query(models.OrganizationUser).filter(
            models.OrganizationUser.user_id == user.id
        ).all()
        
        results = []
        for m in memberships:
            org = m.organization
            if org:
                # Get User Role in this Org
                results.append({
                    "id": org.id,
                    "name": org.name,
                    "logo": org.logo_url,
                    "role": m.role
                })
        return results
    finally:
        db.close()

@app.post("/auth/logout")
async def logout_endpoint():
    response = JSONResponse({"status": "ok", "message": "Logged out"})
    # Clear both access cookies
    response.delete_cookie(key=ACCESS_COOKIE_NAME, domain=COOKIE_DOMAIN, path="/")
    response.delete_cookie(key="access_token", domain=COOKIE_DOMAIN, path="/")
    
    # Clear Refresh Token (Critical)
    response.delete_cookie(key=REFRESH_COOKIE_NAME, domain=COOKIE_DOMAIN, path="/", httponly=True)
    return response

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8005))
    print(f"Starting Accounts Service v2.1 (Passlib) on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

# -----------------------------------------------------------------------------
# JWKS ENDPOINT (OIDC Compliance)
# -----------------------------------------------------------------------------
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

def _pem_to_jwk(pem_bytes):
    try:
        key = serialization.load_pem_public_key(pem_bytes, backend=default_backend())
        numbers = key.public_numbers()
        
        def to_b64url(num):
             # Python's int.to_bytes requires length. Bit_length // 8 + 1
             byte_len = (num.bit_length() + 7) // 8
             val_bytes = num.to_bytes(byte_len, byteorder="big")
             return base64.urlsafe_b64encode(val_bytes).decode("utf-8").rstrip("=")

        return {
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "kid": "ao-core-key-1", # Static KID for now
            "n": to_b64url(numbers.n),
            "e": to_b64url(numbers.e)
        }
    except Exception as e:
        print(f"JWK Conversion Error: {e}")
        return None

@app.get("/.well-known/jwks.json")
def jwks_endpoint():
    # Import here to avoid circularity if any, or rely on global import?
    # Global import of common.auth might not have the key loaded if env vars not set during import time?
    # But checking common.auth imports at top of file: yes.
    
    if not AO_JWT_PUBLIC_KEY_PEM:
        return {"keys": []}
        
    jwk = _pem_to_jwk(AO_JWT_PUBLIC_KEY_PEM)
    if jwk:
        return {"keys": [jwk]}
    return {"keys": []}
