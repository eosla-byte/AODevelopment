from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

# Import from common
# Need to ensure sys path or package structure calls work.
# We will use relative imports assuming running from root 'backend' module context 
# OR we need to adjust sys.path if running as standalone.
# For now, assuming "Modular Monolith" run from root.
from ...common.database import get_user_by_email, save_user, User as CommonUser
from ...common.auth_utils import verify_password, create_access_token, get_password_hash

app = FastAPI(title="AO Core (Auth)")

# Input Models
class LoginRequest(BaseModel):
    username: str
    password: str

# CORS (Allow All for internal/dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/login")
async def login(credentials: LoginRequest):
    user = get_user_by_email(credentials.username)
    
    if not user:
        # Check for default admin creation logic if empty? 
        # For microservice, we assume DB is seeded.
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account locked")

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "name": user.name}
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions
        }
    }

@app.get("/me")
async def get_current_user_info(request: Request):
    # This endpoint relies on Gateway passing user info or Token validation here.
    # For now, simple echo or DB lookup if token passed.
    pass

# Health Check
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AO Core"}
