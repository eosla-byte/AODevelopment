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
from common.database import get_db, SessionExt 
# Note: SessionExt is perfect because we want to connect to EXT_DB_URL by default
from common.models import BimUser, BimOrganization
from common.auth_utils import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

# TEMPLATES
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# DATABASE PROVIDER
# We need a specific provider for External DB if get_db defaults to something else.
# In database.py we made get_db default to SessionOps. 
# We should import get_ext_db if we created it? Or just use SessionExt manually.
# Let's check common/database.py imports availability.
# Assuming we can use:
def get_ext_db():
    db = SessionExt()
    try:
        yield db
    finally:
        db.close()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_ext_db)):
    user = db.query(BimUser).filter(BimUser.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales inválidas"})
    
    # Create Token
    access_token = create_access_token(data={"sub": user.email, "role": user.role, "org": user.organization_id})
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register_submit(
    request: Request, 
    org_name: str = Form(...), 
    full_name: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...),
    db: Session = Depends(get_ext_db)
):
    # Check existing
    existing = db.query(BimUser).filter(BimUser.email == email).first()
    if existing:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email ya registrado"})
        
    # Create Org
    new_org = BimOrganization(
        id=str(uuid.uuid4()),
        name=org_name
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    
    # Create User (Owner)
    new_user = BimUser(
        id=str(uuid.uuid4()),
        organization_id=new_org.id,
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role="Owner"
    )
    db.add(new_user)
    db.commit()
    
    # Auto Login
    access_token = create_access_token(data={"sub": new_user.email, "role": new_user.role, "org": new_org.id})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response
