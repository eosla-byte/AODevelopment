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

# Path Setup to allow importing 'backend.common'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Assumes structure: AODevelopment/backend/services/accounts/main.py
# So we need to go up 3 levels to get to AODevelopment
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if BACKEND_ROOT not in sys.path:
    # Append root for common modules
    sys.path.append(BACKEND_ROOT)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from common.database import get_db, SessionExt 
from common.auth_utils import verify_password, create_access_token, decode_access_token, get_password_hash
from common.models import AccountUser

app = FastAPI(title="AO Accounts & Identity")

# Mount Static
# app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- Dependencies ---
def get_current_admin(request: Request):
    token = request.cookies.get("accounts_access_token")
    if not token:
        return None
    try:
        scheme, _, param = token.partition(" ")
        payload = decode_access_token(param)
        if not payload: 
            return None
        # Check if role is Admin (or sufficient privilege)
        if payload.get("role") != "Admin":
            return None
        return payload 
    except:
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
    db = SessionExt()
    user = db.query(AccountUser).filter(AccountUser.email == email).first()
    db.close()
    
    if not user:
        # Mock Init Admin if no users exist at all?
        # For now, just fail
        return JSONResponse({"status": "error", "message": "Invalid credentials or user not found."}, status_code=401)
        
    if not verify_password(password, user.hashed_password):
        return JSONResponse({"status": "error", "message": "Invalid password."}, status_code=401)
        
    if user.role != "Admin":
         return JSONResponse({"status": "error", "message": "Access restricted to Administrators."}, status_code=403)

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "id": user.id},
        expires_delta=datetime.timedelta(hours=12) # Long session for admin
    )
    
    response = JSONResponse({"status": "ok", "redirect": "/dashboard"})
    response.set_cookie(key="accounts_access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/auth/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("accounts_access_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user = Depends(get_current_admin)):
    if not user: return RedirectResponse("/login")
    
    db = SessionExt()
    users = db.query(AccountUser).all()
    
    # Serialize and Group by Company
    users_by_company = {}
    
    for u in users:
        u_data = {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "company": u.company or "Unassigned",
            "phone": u.phone,
            "role": u.role,
            "status": u.status,
            "access_level": "Project", 
            "added_on": u.created_at.strftime("%Y-%m-%d") if u.created_at else "",
            "docs_access": u.docs_access,
            "insight_access": u.insight_access,
            "services_access": u.services_access or {}
        }
        
        company_key = u_data["company"]
        if company_key not in users_by_company:
            users_by_company[company_key] = []
        users_by_company[company_key].append(u_data)
        
    db.close()
    
    # Sort companies alphabetically, put 'Unassigned' last if present
    company_names = sorted(users_by_company.keys())
    if "Unassigned" in company_names:
        company_names.remove("Unassigned")
        company_names.append("Unassigned")
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "users_by_company": users_by_company,
        "company_list": company_names,
        "admin_email": user["sub"]
    })

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
    
    db = SessionExt()
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
    
    db = SessionExt()
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
    
    db = SessionExt()
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
    db = SessionExt()
    user = db.query(AccountUser).filter(AccountUser.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    db.close()
    return JSONResponse({"status": "ok", "message": "User deleted"})

# Setup Script Route (Temporary, to create first admin if none)
@app.get("/setup_initial_admin")
async def setup_admin():
    db = SessionExt()
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8005))
    print(f"Starting Accounts Service on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
