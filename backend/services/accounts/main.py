from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
import uvicorn
import os
import sys
import uuid
import datetime
from typing import List, Optional



# Path Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Local imports (common is now partially vendored or in path)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from common.database import get_db, SessionCore 
from common.auth import create_access_token, create_refresh_token, decode_token
from common.auth_utils import verify_password, get_password_hash # Keep password utils
import common.models as models 
from common.models import AccountUser 

# Initialize Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

app = FastAPI(title="AO Accounts Service")

# Mount Static if exists
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    # Create it to prevent future errors? Or just don't mount.
    # User asked to mount it.
    os.makedirs(STATIC_DIR, exist_ok=True)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup_event():
    run_db_fix()

# ... (version check same)

# ... (dependencies)
def get_current_admin(request: Request):
    token = request.cookies.get("accounts_access_token")
    if not token:
        return None
    try:
        # Decode using common auth (RS256 Public Key)
        payload = decode_token(token)
        if not payload: 
            return None
            
        # Check if role is Admin (or sufficient privilege)
        if payload.get("role") not in ["Admin", "SuperAdmin"]:
            return None
        return payload 
    except Exception as e:
        return None

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
    Returns: (org_id, role, services_list) or (None, None, None)
    """
    # 1. Check Last Active
    if user.last_active_org_id:
        membership = db.query(models.OrganizationUser).filter(
            models.OrganizationUser.user_id == user.id,
            models.OrganizationUser.organization_id == user.last_active_org_id
        ).first()
        if membership:
            return _build_context(db, membership)
            
    # 2. Check Total Memberships
    memberships = db.query(models.OrganizationUser).filter(
        models.OrganizationUser.user_id == user.id
    ).all()
    
    if len(memberships) == 1:
        # Auto-select the only one
        return _build_context(db, memberships[0])
        
    # 3. Multiple or None -> Require Selection
    return None, None, None

def _build_context(db, membership):
    # Get Services from Organization permissions
    # For now, we might default to user global services OR org specific.
    # Architecture says: "Services come from Entitlements"
    # Let's merge User Global + Org Entitlements? 
    # Or just use User Global for now as per current schema?
    # Current schema has `user.services_access` (JSON).
    # Let's stick to `user.services_access` for the list of enabled apps,
    # but maybe filtered by Org? 
    # Simpler: Just use user.services_access keys where value is True.
    
    services = []
    if membership.user.services_access:
        services = [k for k, v in membership.user.services_access.items() if v]
        # Normalize keys to lowercase slugs if needed (AOdailyWork -> daily)
        # Mapping:
        slug_map = {
            "AODailyWork": "daily",
            "AOPlanSystem": "bim",
            "AOBuild": "build",
            "AO Clients": "portal",
            "AOdev": "api",
            "AO HR & Finance": "finance"
        }
        services = [slug_map.get(s, s.lower()) for s in services]
        
    return membership.organization_id, membership.role, services

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user = Depends(get_current_admin)):
    if user:
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

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
        
        # Token Claims (Standardized)
        claims = {
            "sub": user.id,   # Use UUID as sub
            "email": user.email,
            "role": org_role if org_role else user.role, 
            "org_id": org_id, 
            "services": services or []
        }
        
        # Determine Response Status
        status_response = "ok"
        redirect_url = "/dashboard" 
        
        if not org_id:
            status_response = "select_org"
            redirect_url = "/select-org"
            
        # ACCESS TOKEN (Short Lived - 15 Mins)
        access_token = create_access_token(data=claims)
        
        # REFRESH TOKEN (Long Lived - 7 Days)
        refresh_claims = {"sub": user.id, "email": user.email} # Minimal data for refresh
        refresh_token = create_refresh_token(data=refresh_claims)
        
        response = JSONResponse({"status": status_response, "redirect": redirect_url, "user": {"id": user.id, "email": user.email}})
        
        # COOKIE: ACCOUNTS_ACCESS_TOKEN (HttpOnly, Secure, Domain)
        response.set_cookie(
            key="accounts_access_token", 
            value=access_token, 
            httponly=True,
            samesite="none",
            secure=True, 
            domain=".somosao.com"
        )
        response.set_cookie(
            key="accounts_refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="none",
            secure=True, 
            domain=".somosao.com",
            max_age=7 * 24 * 60 * 60
        )
        
        print(f"Login Success: {user.email} (Org: {org_id})")
        return response
    finally:
        db.close()

@app.get("/auth/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("accounts_access_token", domain=".somosao.com")
    # Also delete for host only just in case
    response.delete_cookie("accounts_access_token")
    response.delete_cookie("refresh_token", domain=".somosao.com")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, org_id: Optional[str] = None, user_jwt = Depends(get_current_admin)):
    if not user_jwt: return RedirectResponse("/login")
    
    db = SessionCore()
    user_db = db.query(AccountUser).filter(AccountUser.email == user_jwt["sub"]).first()
    
    if not user_db:
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
    user = db.query(AccountUser).filter(AccountUser.email == user_jwt["sub"]).first()
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
    refresh_token = request.cookies.get("accounts_refresh_token")
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
            
            access_token = create_access_token(data=claims)
            
            response = JSONResponse({"status": "ok", "message": "Token refreshed", "org_id": org_id})
            
            # 1. ACCOUNTS Cookie
            response.set_cookie(
                key="accounts_access_token", 
                value=access_token, 
                httponly=True,
                samesite="none",
                secure=True, 
                domain=".somosao.com"
            )
            
            # 2. FALLBACK Cookie
            response.set_cookie(
                key="access_token", 
                value=access_token, 
                httponly=True,
                samesite="lax",
                secure=False
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
    token = request.cookies.get("accounts_access_token") 
    refresh = request.cookies.get("accounts_refresh_token")
    
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
        
        access_token = create_access_token(data=claims)
        
        response = JSONResponse({"status": "ok", "message": "Organization selected"})
        
        response.set_cookie(
            key="accounts_access_token", 
            value=access_token, 
            httponly=True,
            samesite="none",
            secure=True, 
            domain=".somosao.com"
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            secure=False
        )
        return response
    finally:
        db.close()

@app.get("/api/my-organizations")
async def get_my_organizations_endpoint(request: Request):
    # Manual Auth Check (User level)
    token = request.cookies.get("accounts_access_token")
    user_email = None
    if token:
         payload = decode_token(token)
         if payload: user_email = payload.get("sub")
         
    # Allow via Refresh token too? For the "Select Org" screen when Access is expired/missing?
    if not user_email:
        refresh = request.cookies.get("accounts_refresh_token")
        if refresh:
            payload = decode_token(refresh)
            if payload and payload.get("type") == "refresh":
                 user_email = payload.get("sub")

    if not user_email:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    db = SessionCore() 
    try:
        user = db.query(AccountUser).filter(AccountUser.email == user_email).first()
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
async def logout():
    response = JSONResponse({"status": "ok", "message": "Logged out"})
    # Clear both access cookies
    response.delete_cookie(key="accounts_access_token", domain=".somosao.com", path="/")
    response.delete_cookie(key="access_token", domain=".somosao.com", path="/")
    
    # Clear Refresh Token (Critical)
    response.delete_cookie(key="accounts_refresh_token", domain=".somosao.com", path="/", httponly=True)
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
    from common.auth import JWT_PUBLIC_KEY_PEM
    
    if not JWT_PUBLIC_KEY_PEM:
        return {"keys": []}
        
    jwk = _pem_to_jwk(JWT_PUBLIC_KEY_PEM)
    if jwk:
        return {"keys": [jwk]}
    return {"keys": []}
