from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
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

# Local imports (common is now partially vendored or in path)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from common.database import get_db, SessionCore 
from common.auth_utils import verify_password, create_access_token, decode_access_token, get_password_hash
import common.models as models 
from common.models import AccountUser

from routers import organizations

app = FastAPI(title="AO Accounts & Identity")

app.include_router(organizations.router)

@app.on_event("startup")
def startup_event():
    """
    Ensure default 'AO Development' organization exists and Admin is SuperAdmin.
    """
    db = SessionCore()
    try:
        # 1. Update/Ensure Admin is SuperAdmin
        admin_email = "admin@somosao.com"
        admin = db.query(AccountUser).filter(AccountUser.email == admin_email).first()
        if admin:
            # FORCE RESET PASSWORD TO 'admin123' to ensure access
            # print(f"Reseting password for {admin_email}...") # Commented out to reduce noise
            # admin.hashed_password = get_password_hash("admin123")
            
            if admin.role != "SuperAdmin":
                print(f"Promotion {admin_email} to SuperAdmin...")
                admin.role = "SuperAdmin"
            db.commit()
        else:
            # Create if not exists
            print(f"Creating Admin User {admin_email}...")
            new_admin = AccountUser(
                id=str(uuid.uuid4()),
                email=admin_email,
                full_name="System Admin",
                hashed_password=get_password_hash("admin123"),
                role="SuperAdmin",
                status="Active"
            )
            db.add(new_admin)
            db.commit()
            admin = new_admin
                
        # 2. Ensure Default Organization
        default_org_name = "AO Development"
        org = db.query(models.Organization).filter(models.Organization.name == default_org_name).first()
        if not org:
            print(f"Creating default Organization: {default_org_name}")
            new_org = models.Organization(
                id=str(uuid.uuid4()),
                name=default_org_name,
                status="Active"
            )
            db.add(new_org)
            db.commit()
            org = new_org
            
        # 3. Ensure Admin belongs to Default Org
        if admin and org:
            details = db.query(models.OrganizationUser).filter(
                models.OrganizationUser.organization_id == org.id,
                models.OrganizationUser.user_id == admin.id
            ).first()
            if not details:
                print(f"Adding Admin to {default_org_name}...")
                membership = models.OrganizationUser(
                    organization_id=org.id,
                    user_id=admin.id,
                    role="Admin"
                )
                db.add(membership)
                db.commit()
                
    except Exception as e:
        print(f"Startup Logic Error: {e}")
    finally:
        db.close()

@app.get("/version_check")
def version_check():
    return {"version": "v5_cookie_debug", "timestamp": datetime.datetime.now().isoformat()}

# Mount Static
# app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- Dependencies ---
def get_current_admin(request: Request):
    token = request.cookies.get("accounts_access_token")
    if not token:
        print("Auth Failed: No 'accounts_access_token' cookie found.")
        return None
    try:
        scheme, _, param = token.partition(" ")
        if not param:
             # Maybe raw token without Bearer prefix?
             param = token
             
        payload = decode_access_token(param)
        if not payload: 
            print("Auth Failed: Invalid Token signature.")
            return None
        # Check if role is Admin (or sufficient privilege)
        if payload.get("role") != "Admin" and payload.get("role") != "SuperAdmin":
            print(f"Auth Failed: Insufficient Role {payload.get('role')}")
            return None
        return payload 
    except Exception as e:
        print(f"Auth Failed: Exception {e}")
        return None

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
    print(f"Login Attempt: '{email}'")
    email = email.strip().lower()
    
    db = SessionCore()
    try:
        user = db.query(AccountUser).filter(AccountUser.email == email).first()
        
        if not user:
            print(f"Login Failed: User '{email}' not found in DB.")
            return JSONResponse({"status": "error", "message": f"User '{email}' not found."}, status_code=401)
            
        print(f"User found: {user.id}. Role: {user.role}.")
        print(f"Stored Hash (First 10 chars): {user.hashed_password[:10] if user.hashed_password else 'NONE'}...")
        
        verification = verify_password(password, user.hashed_password)
        print(f"Verification Result: {verification}")
        
        if not verification:
            print("Login Failed: Password mismatch.")
            return JSONResponse({"status": "error", "message": "Invalid password (hash mismatch)."}, status_code=401)
            
        valid_roles = ["Admin", "SuperAdmin"]
        if user.role not in valid_roles:
             # Check Organization Memberships for "Admin" role?
             is_org_admin = db.query(models.OrganizationUser).filter(
                models.OrganizationUser.user_id == user.id,
                models.OrganizationUser.role == "Admin"
             ).first()

             if not is_org_admin:
                 return JSONResponse({"status": "error", "message": "Access restricted to Administrators."}, status_code=403)

        access_token = create_access_token(
            data={
                "sub": user.email, 
                "role": user.role, 
                "id": user.id,
                "services_access": user.services_access or {}
            },
            expires_delta=datetime.timedelta(hours=12)
        )
        
        response = JSONResponse({"status": "ok", "redirect": "/dashboard"})
        # Use Lax for standard navigation
        response.set_cookie(
            key="accounts_access_token", 
            value=f"Bearer {access_token}", 
            httponly=True,
            samesite="lax",
            secure=False, # Set to True if strictly SSL coverage
            domain=".somosao.com" # Allow sharing with *.somosao.com
        )
        print(f"Cookie set for {user.email}")
        return response
    finally:
        db.close()

@app.get("/auth/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("accounts_access_token", domain=".somosao.com")
    # Also delete for host only just in case
    response.delete_cookie("accounts_access_token")
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
    # Permissions
    access_aodev: bool = Form(False), # If checkboxes are unchecked, they might not send data? Javascript should handle sending booleans explicitly.
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
    
    # Update Services
    # We construct the dict again. 
    # Note: If we hadpartial updates we'd merge, but here the UI will likely send all.
    user.services_access = {
        "AOdev": access_aodev,
        "AO HR & Finance": access_hr,
        "AO Projects": access_projects,
        "AO Clients": access_clients,
        "AODailyWork": access_daily,
        "AOPlanSystem": access_bim,
        "AOBuild": access_build
    }
    
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
        db.delete(user)
        db.commit()
    db.close()
    return JSONResponse({"status": "ok", "message": "User deleted"})

# Setup Script Route (Temporary, to create first admin if none)
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8005))
    print(f"Starting Accounts Service on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
