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
from sqlalchemy.orm import Session  # for type hints



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
# from common.db_migration_entitlements import run_entitlements_migration # MOVED TO LIFESPAN
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

import logging
logger = logging.getLogger("uvicorn")

# -----------------------------------------------------------------------------
# ENTITLEMENTS VERIFICATION (Module Level)
# -----------------------------------------------------------------------------
is_prod = (
    (os.getenv("RAILWAY_ENVIRONMENT_NAME", "") or "").lower() == "production"
    or (os.getenv("AO_ENV", "") or "").lower() == "production"
)

if is_prod:
    logger.info("[ENTITLEMENTS] Production: skipping auto-migration. Verifying schema...")
    try:
        from sqlalchemy import text
        with SessionCore() as db_check:
            db_check.execute(text("SELECT 1 FROM accounts_entitlements LIMIT 1"))
        logger.info("[ENTITLEMENTS] Production schema verified OK.")
    except Exception as e:
        logger.warning(f"[ENTITLEMENTS] Production schema verification failed: {type(e).__name__}")
        logger.warning(f"Error details: {e}")
        logger.error("[ENTITLEMENTS] CRITICAL: Schema verification failed in PROD. Exiting to prevent crash loops.")
        sys.exit(1)
else:
    logger.info("[ENTITLEMENTS] Non-prod: running auto-migration/seeding...")
    try:
        from common.db_migration_entitlements import run_entitlements_migration
        run_entitlements_migration()
    except Exception as e:
        logger.warning(f"[ENTITLEMENTS] Auto-migration skipped or failed: {e}")

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
        # run_db_fix() # DISABLED: Moved to Alembic
        pass
        
    except Exception as e:
        print(f"❌ [STARTUP] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        if db:
            db.close()
            
    yield
    print("🛑 [SHUTDOWN] Application stopping...")

app = FastAPI(title="AO Accounts Service", lifespan=lifespan)


# ... (version check same)
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "accounts", "version": "v1.0"}

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
    # Check Role
    role = (user.get("role") or "").strip()
    role_norm = role.lower()
    email = (user.get("email") or "").lower()
    # Allow platform admins even if role casing differs.
    if role_norm not in ["admin", "superadmin"] and email not in [e.lower() for e in SUPER_ADMIN_EMAILS]:
         print(f"DEBUG: Role '{role}' denied admin access.")
         # Return None to trigger 401/Redirect in caller
         return None
    return user

# --- DB Migration Helper ---
# --- DB Migration Helper ---
# def run_db_fix():
#     # DISABLED: Logic moved to Alembic interactions
#     pass

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
             # HARDENING: Fallback to email is NO LONGER ALLOWED.
             # If user model has no ID, this is a critical data error.
             print(f"❌ [LOGIN] CRITICAL: User {email} has no UUID (Legacy AppUser?). Login blocked.")
             return JSONResponse({"status": "error", "message": "Account migration required. Contact Support."}, status_code=403)
             # real_user_id = user.email # REMOVED

        # Fetch Entitlements Version for Cache Invalidation
        entitlements_version = 1
        if org_id:
             try:
                 org_obj = db.query(models.Organization).filter(models.Organization.id == org_id).first()
                 if org_obj:
                     entitlements_version = getattr(org_obj, "entitlements_version", 1)
             except Exception:
                 pass

        # Token Claims (Standardized)
        claims = {
            "sub": str(real_user_id),   # Use UUID or Email as sub
            "email": user.email,
            "role": org_role if org_role else user.role, 
            "platform_role": "super_admin" if is_super_admin else None,
            "org_id": org_id, 
            "entitlements_version": entitlements_version,
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
        # HARDENING: Short Max-Age (1 Hour) to encourage migration
        response.set_cookie(
            key="access_token", 
            value=access_token, 
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE, 
            domain=COOKIE_DOMAIN,
            path="/",
            max_age=3600 # 1 Hour Deprecation Window
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
        # V3 ENTITLEMENTS UPDATE
        # 1. Update/Create OrgEntitlement
        ent = db.query(models.OrgEntitlement).filter(
            models.OrgEntitlement.org_id == org_id,
            models.OrgEntitlement.entitlement_key == data.service_slug
        ).first()
        
        if ent:
            ent.enabled = data.is_active
        else:
            # Check if valid entitlement key
            master = db.query(models.Entitlement).filter(models.Entitlement.id == data.service_slug).first()
            if not master:
                 # Auto-create master if missing? Or error?
                 # Let's error to be safe, or auto-create for dev speed.
                 # Error is safer.
                 # Actually, for "daily", "bim" etc they should exist.
                 if not master:
                     return JSONResponse({"detail": f"Invalid Service Slug: {data.service_slug}"}, status_code=400)
            
            ent = models.OrgEntitlement(
                org_id=org_id,
                entitlement_key=data.service_slug,
                enabled=data.is_active
            )
            db.add(ent)
            
        # 2. BUMP VERSION (Critical for Cache Invalidation)
        org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
        if org:
            current_ver = getattr(org, "entitlements_version", 1)
            org.entitlements_version = current_ver + 1
            print(f"🔄 [ENTITLEMENTS] Bumped Org {org_id} version to {org.entitlements_version}")
            
        # 3. Legacy Sync (Optional, for ServicePermission table if still used)
        # We perform it to be safe during transition
        try:
            perm = db.query(models.ServicePermission).filter(
                models.ServicePermission.organization_id == org_id,
                models.ServicePermission.service_slug == data.service_slug
            ).first()
            if perm:
                perm.is_active = data.is_active
            else:
                db.add(models.ServicePermission(
                    id=str(uuid.uuid4()),
                    organization_id=org_id,
                    service_slug=data.service_slug,
                    is_active=data.is_active
                ))
        except Exception:
            pass # Ignore legacy errors
            
        db.commit()
        return {"status": "ok", "new_version": org.entitlements_version if org else None}
    except Exception as e:
        db.rollback()
        print(f"toggle_org_service ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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
    
    db = SessionCore()
    # FIX: sub is UUID (id), not email.
    user_id = user_jwt.get("sub")
    user_email = user_jwt.get("email")
    print(f"DEBUG: Lookup User ID: {user_id} (Email fallback: {user_email})")
    
    user_db = db.query(AccountUser).filter(AccountUser.id == user_id).first()
    
    if not user_db and user_email:
        print(f"DEBUG: User not found by ID {user_id}, trying email {user_email}...")
        user_db = db.query(AccountUser).filter(AccountUser.email == user_email).first()
    
    if not user_db:
        print(f"DEBUG: DASHBOARD REDIRECT: token_sub={user_id} token_email={user_email} reason=user_not_found_in_db")
        db.close()
        return RedirectResponse("/login")

    view_context = {
        "request": request,
        "user": user_db,
        "view_mode": "member", # member, org_admin, super_admin
        "organizations": [],
        "current_org": None,
        # Updated Service List (Public Services)
        "available_services": ["daily", "plans", "build", "clients", "plugin"]
    }

    # 1. SUPER ADMIN VIEW
    if user_db.role == "SuperAdmin":
        if org_id:
            # Switch to Org Admin View for specific org
            target_org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
            if target_org:
                view_context["view_mode"] = "org_admin"
                view_context["current_org"] = target_org
        else:
            view_context["view_mode"] = "super_admin"
            # Fetch all organizations with member counts
            orgs = db.query(models.Organization).all()
            view_context["organizations"] = orgs

    # 2. ORG ADMIN VIEW (If not super admin, but IS an admin of a specific org)
    else:
        # distinct Logic: Find memberships where role='Admin'
        # If org_id provided, check if member of THAT org
        query = db.query(models.OrganizationUser).filter(
            models.OrganizationUser.user_id == user_db.id,
            models.OrganizationUser.role == "Admin"
        )
        
        if org_id:
             query = query.filter(models.OrganizationUser.organization_id == org_id)
             
        membership = query.first()
        
        if membership:
            view_context["view_mode"] = "org_admin"
            view_context["current_org"] = membership.organization
        else:
            # 3. STATIC MEMBER VIEW (Apps Launcher)
            view_context["view_mode"] = "member"
    
    # db.close() # TemplateResponse might need lazy loads? 
    # Better to eager load or keep session open if Jinja needs it?
    # For safety with simple relationships, we can close if we eagerly loaded.
    # But SqlAlchemy objects detach if session closes.
    # We will close APTER template rendering? No, template response renders immediately? 
    # Actually TemplateResponse is a background task wrapper effectively, but vars need to be ready.
    # Let's simple query active objects into Pydantic or Dictionaries if issues arise.
    # For now, let's keep database objects but we must be careful.
    # Actually, fastAPI depends dependency closes DB session? 
    # If using yield in get_db, yes. But here we manually opened SessionCore().
    # We should NOT close it before return if we pass ORM objects that need lazy loading.
    # But we should ensure it closes eventually.
    # Hack: Convert to list/dict before closing.
    
    return templates.TemplateResponse("dashboard.html", view_context)

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
        user.services_access = user.services_access or {}
        db.commit()
    db.close()
    return "User promoted to SuperAdmin"

@app.get("/setup_initial_admin")
async def setup_admin():
    """One-time bootstrap endpoint.
    Creates a platform-level superadmin user (and optionally an admin) without requiring an org context.
    Safe to call multiple times.
    """
    db = SessionCore()
    try:
        # Users to ensure exist
        seed_users = [
            {
                "email": "superadmin@somosao.com",
                "password": "supertata123",
                "role": "superadmin",
                "full_name": "Super Admin",
            },
            # Keep the original admin account as an admin (not org-bound)
            {
                "email": "admin@somosao.com",
                "password": None,  # don't overwrite
                "role": "admin",
                "full_name": "Administrator",
            },
        ]

        def _set_if(obj, attr, value):
            if value is None:
                return
            if hasattr(obj, attr):
                setattr(obj, attr, value)

        def _ensure_user(email: str, password: str | None, role: str, full_name: str):
            # Find by email if the model supports it
            email_col = getattr(AccountUser, "email", None)
            q = db.query(AccountUser)
            if email_col is not None:
                existing = q.filter(email_col == email).first()
            else:
                # Fallback: try username
                username_col = getattr(AccountUser, "username", None)
                if username_col is None:
                    return None, False
                existing = q.filter(username_col == email).first()

            if existing:
                # Ensure role is correct (don't touch password unless explicitly provided)
                _set_if(existing, "role", role)
                _set_if(existing, "full_name", full_name)
                _set_if(existing, "is_active", True)
                return existing, False

            u = AccountUser()

            # Primary key variants
            if hasattr(u, "id"):
                u.id = str(uuid.uuid4())
            elif hasattr(u, "user_id"):
                u.user_id = str(uuid.uuid4())
            elif hasattr(u, "uid"):
                u.uid = str(uuid.uuid4())

            # Core identity fields
            _set_if(u, "email", email)
            _set_if(u, "username", email)
            _set_if(u, "full_name", full_name)
            _set_if(u, "role", role)
            _set_if(u, "is_active", True)

            # Org context for platform users should be empty / None
            _set_if(u, "org_id", None)
            _set_if(u, "active_org_id", None)

            # Optional permissions/flags
            _set_if(u, "services_access", {})
            _set_if(u, "services_count", 0)

            # Password
            if password:
                hashed = hash_password(password)
                # common field names
                _set_if(u, "hashed_password", hashed)
                _set_if(u, "password_hash", hashed)
                _set_if(u, "password", hashed)

            db.add(u)
            db.commit()
            db.refresh(u)
            return u, True

        results = []
        for su in seed_users:
            user_obj, created = _ensure_user(
                su["email"], su["password"], su["role"], su["full_name"]
            )
            if user_obj is None:
                results.append({"email": su["email"], "status": "failed (model mismatch)"})
            else:
                results.append({"email": su["email"], "status": "created" if created else "exists"})

        return {"ok": True, "results": results}
    finally:
        db.close()


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
    """Return organizations visible to the current user.

    - Normal users: orgs where they are a member.
    - Platform admins/superadmins: all orgs (so they can manage tenants/users).
    """
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    user_email = None
    role_norm = ""

    if token:
        payload = decode_token(token)
        if payload:
            user_email = (payload.get("sub") or payload.get("email") or "").strip()
            role_norm = ((payload.get("role") or "")).strip().lower()

    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if (not user_email) and refresh_token:
        refresh_payload = decode_token(refresh_token, expected_type="refresh")
        if refresh_payload:
            user_email = (refresh_payload.get("sub") or refresh_payload.get("email") or "").strip()
            role_norm = ((refresh_payload.get("role") or "")).strip().lower()

    if not user_email:
        return []

    db = SessionCore()
    try:
        email_col = getattr(AccountUser, "email", None)
        if email_col is None:
            return []

        user_db = db.query(AccountUser).filter(email_col == user_email).first()
        if not user_db:
            return []

        # Platform admins see ALL orgs
        is_platform_admin = (role_norm in ["admin", "superadmin"]) or (user_email.lower() in [e.lower() for e in SUPER_ADMIN_EMAILS])
        if is_platform_admin:
            orgs = db.query(models.Organization).all()
            return [
                {
                    "id": o.id,
                    "name": getattr(o, "name", None),
                    "role": "superadmin" if role_norm == "superadmin" else "admin",
                    "is_active": True,
                }
                for o in orgs
            ]

        # Normal users: via membership table
        member_org_ids = (
            db.query(models.OrganizationUser.org_id)
            .filter(models.OrganizationUser.user_id == getattr(user_db, "id", getattr(user_db, "user_id", None)))
            .all()
        )
        member_org_ids = [row[0] for row in member_org_ids]

        if not member_org_ids:
            return []

        orgs = db.query(models.Organization).filter(models.Organization.id.in_(member_org_ids)).all()

        # map roles
        roles = {
            r.org_id: r.role
            for r in db.query(models.OrganizationUser)
            .filter(models.OrganizationUser.user_id == getattr(user_db, "id", getattr(user_db, "user_id", None)))
            .all()
        }

        return [
            {
                "id": o.id,
                "name": getattr(o, "name", None),
                "role": roles.get(o.id, "user"),
                "is_active": getattr(o, "is_active", True),
            }
            for o in orgs
        ]
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