
import bcrypt
from datetime import datetime, timedelta
from typing import Optional

# -----------------------------------------------------------------------------
# ADAPTER FOR RS256 MIGRATION
# -----------------------------------------------------------------------------
# We proxy calls to the new common.auth module to ensure consistency.
# This file is kept for backward compatibility with existing imports.

from .auth import (
    create_access_token as _create_access_token_rs256,
    decode_token as _decode_token_rs256,
    oauth2_scheme
)

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    if not hashed_password: return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Proxy to common.auth.create_access_token (RS256).
    """
    return _create_access_token_rs256(data, expires_delta)

def decode_access_token(token: str):
    """
    Proxy to common.auth.decode_token (RS256).
    """
    return _decode_token_rs256(token)

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

# Reuse scheme from common.auth
# oauth2_scheme is imported above

def verify_token_dep(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme)
):
    # Debug Logging
    # print(f"DEBUG AUTH: Header Token: {True if token else False}")
    
    # 1. Try Token from Header (OAuth2PasswordBearer) -> 2. If missing, Try Cookie
    if not token:
        cookie_token = request.cookies.get("accounts_access_token")
        if cookie_token:
            if cookie_token.startswith("Bearer "):
                token = cookie_token.split(" ")[1]
            else:
                token = cookie_token
        
    # 3. Fallback: Query Param (Bulletproof for Iframes where cookies are blocked)
    if not token:
        token = request.query_params.get("token") or request.query_params.get("access_token")

    if not token:
        # print("❌ [DEBUG AUTH] FAILED: No token found in Header, Cookie, OR Query Params.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (No Header or Cookie)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # print(f"✅ [DEBUG AUTH] Token Found. Decoding...")
    payload = decode_access_token(token)
    if payload is None:
        # print("DEBUG AUTH: Token decode failed (Invalid or Expired).")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload # Returns the dict (sub, role, etc)


# --- Multi-Tenant Context Enforcement ---
# Imports inside to avoid circular deps if possible, but standard practice is top-level.
# We'll import here to be safe given the vendoring structure.
import common.models as models
from common.database import SessionCore

def require_org_access(service_slug: str):
    """
    Factory that returns a dependency to enforce:
    1. Organization Context (Header X-Organization-ID)
    2. User Membership in Org
    3. Org Access to Service
    4. User Access to Service
    """
    async def dependency(
        request: Request, 
        current_user: dict = Depends(get_current_user)
    ):
        org_id = request.headers.get("X-Organization-ID")
        
        # If no Org ID and user is SuperAdmin, MAYBE allow? 
        # But specifically for public services (BIM, Daily), we NEED a context.
        if not org_id:
             raise HTTPException(status_code=400, detail="Missing Organization Context (X-Organization-ID)")
             
        db = SessionCore()
        try:
            user_id = current_user.get("id")
            # 1. Check Membership & User-Specific Service Permission
            membership = db.query(models.OrganizationUser).filter(
                models.OrganizationUser.organization_id == org_id,
                models.OrganizationUser.user_id == user_id
            ).first()
            
            if not membership:
                raise HTTPException(status_code=403, detail="You are not a member of this Organization")
                
            # Check User Permission for this service (if set)
            # permissions is a JSON dict e.g. {"bim": true}
            # If key is missing, default to False? Or True? 
            # Logic: If Org has it, does User have it? 
            # In Dashboard we have checkboxes. So likely defaults to False if not explicitly set.
            # But let's be lenient: If permissions dict is empty/null, maybe they are Admin?
            # Admins always access? 
            is_org_admin = membership.role == "Admin"
            
            # Simple check:
            user_perms = membership.permissions or {}
            # Check explicit toggle. If missing, assume FALSE unless Admin? 
            # Let's assume FALSE to be safe, requiring explicit assignment.
            # EXCEPT if functionality hasn't run yet. 
            # Let's enforce: MUST BE TRUE.
            if not is_org_admin and not user_perms.get(service_slug):
                 raise HTTPException(status_code=403, detail=f"You do not have access to {service_slug} in this Organization")

            # 2. Check Organization Service Permission (Master Switch)
            org_perm = db.query(models.ServicePermission).filter(
                models.ServicePermission.organization_id == org_id,
                models.ServicePermission.service_slug == service_slug,
                models.ServicePermission.is_active == True
            ).first()
            
            if not org_perm:
                raise HTTPException(status_code=403, detail=f"Organization does not have access to {service_slug}")
                
            # Return Context
            return {
                "org_id": org_id,
                "user_id": user_id,
                "role": membership.role,
                "service_slug": service_slug
            }
            
        finally:
            db.close()
            
    return dependency
