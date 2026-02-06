from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import uuid
import datetime
from passlib.context import CryptContext
from jose import JWTError, jwt

# Import Shared Modules
from common.database import SessionCore 
from common.models import AccountUser
from common.auth_utils import create_access_token # Removed verify_password, get_password_hash imports

# Local Password Context (Bypassing stale shared code issue)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password_local(plain, hashed):
    if not hashed: return False
    # REMOVED try/except to debug crashes
    return pwd_context.verify(plain, hashed)

router = APIRouter(prefix="/auth", tags=["Auth"])

# TEMPLATES
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Dependency for Core DB (where Accounts live)
def get_core_db_dep():
    db = SessionCore()
    try:
        yield db
    finally:
        db.close()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_core_db_dep)):
    try:
        # Authenticate against Central Accounts
        user = db.query(AccountUser).filter(AccountUser.email == email).first()
        
    # DEBUG: Print user status to logs
        if user:
            print(f"Login Attempt: {email} | Found User. | Hash: {user.hashed_password[:15]}...")
        else:
            print(f"Login Attempt: {email} | User NOT Found.")

        if not user:
             return templates.TemplateResponse("login.html", {"request": request, "error": "Usuario no encontrado (Check DB Connection/Email)"})

        # Verify Password with precise error catch
        valid_pwd = False
        try:
            valid_pwd = verify_password_local(password, user.hashed_password)
        except Exception as e:
             import traceback
             print(f"Pwd Verify Crash: {e}")
             traceback.print_exc()
             return templates.TemplateResponse("login.html", {"request": request, "error": f"Error verificando password: {str(e)}"})

        if not valid_pwd:
             return templates.TemplateResponse("login.html", {"request": request, "error": "Contraseña incorrecta (Hash Mismatch)"})
        
        # Check Service Access
        services_access = user.services_access or {}
        if not services_access.get("AOPlanSystem", False):
             return templates.TemplateResponse("login.html", {"request": request, "error": "Tu usuario existe pero NO tiene acceso a 'AOPlanSystem'."})

    
        # Create Token (Mirroring capabilities of Accounts Service)
        access_token = create_access_token(data={
            "sub": user.email,
            "id": user.id, # Required for Dashboard lookups 
            "role": user.role, 
            "org": user.company,
            "services_access": services_access
        })
        
        response = RedirectResponse(url="/dashboard", status_code=303)
        # Standardize to 'accounts_access_token' for shared auth compatibility
        # Set domain for SSO
        response.set_cookie(
            key="accounts_access_token", 
            value=f"Bearer {access_token}", 
            httponly=True,

            samesite="none",
            domain=".somosao.com",
            secure=True # Required for SameSite=None
        )
        return response
    except Exception as e:
        import traceback
        error_msg = f"Error Interno: {str(e)} - {traceback.format_exc()}"
        print(error_msg)
        return templates.TemplateResponse("login.html", {"request": request, "error": error_msg})

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("accounts_access_token", domain=".somosao.com")
    # Also delete host-only just in case
    response.delete_cookie("accounts_access_token") 
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    # Registration is now centralized
    # We can redirect to accounts or show a message
    return RedirectResponse("https://accounts.somosao.com/login", status_code=303)
