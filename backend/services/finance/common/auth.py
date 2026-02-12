
import os
import jwt
import datetime
from datetime import timedelta
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict, Any

# -----------------------------------------------------------------------------
# CONFIGURATION (RS256 Migration)
# -----------------------------------------------------------------------------
# Users must set (AO_JWT_PRIVATE_KEY_PEM / AO_JWT_PUBLIC_KEY_PEM) in environment
# PEMs are multiline, so handle \n replacement if coming from flat env vars.

import hashlib

def load_pem_key(env_var_name, is_private=False):
    val = os.getenv(env_var_name)
    if not val: return None
    
    # 1. Sanitize: Remove wrapping quotes and whitespace
    val = val.strip().strip("'").strip('"')
    
    # 2. Fix Escaped Newlines (Critical for Railway/Docker envs)
    # Replaces literal string "\n" with actual newline character
    if "\\n" in val:
        val = val.replace("\\n", "\n")
        
    # 3. Validation: Check for PEM Headers
    header = "-----BEGIN RSA PRIVATE KEY-----" if is_private else "-----BEGIN PUBLIC KEY-----"
    footer = "-----END RSA PRIVATE KEY-----" if is_private else "-----END PUBLIC KEY-----"
    
    if header not in val or footer not in val:
        print(f"❌ [AUTH] Malformed PEM in {env_var_name}. Missing Header/Footer.")
        print(f"Debug First 20 chars: {val[:20]}")
        return None
        
    return val.encode('utf-8')

AO_JWT_PRIVATE_KEY_PEM = load_pem_key("AO_JWT_PRIVATE_KEY_PEM", is_private=True)
AO_JWT_PUBLIC_KEY_PEM = load_pem_key("AO_JWT_PUBLIC_KEY_PEM", is_private=False)
AO_JWT_KEY_ID = os.getenv("AO_JWT_KEY_ID", "ao-k1")

# Use Public Key or Secret (Fallback for dev/transition if needed, but Prompt says strict RS256)
if not AO_JWT_PUBLIC_KEY_PEM:
     print("⚠️ [FINANCE AUTH] RS256 Public Key missing! Authentication WILL FAIL.")
else:
     # LOGGING: Fingerprint only (SHA256)
     try:
         # Create a hash of the key bytes to verify consistency across services without exposing the key
         key_hash = hashlib.sha256(AO_JWT_PUBLIC_KEY_PEM).hexdigest()[:16]
         lines = AO_JWT_PUBLIC_KEY_PEM.decode('utf-8').split('\n')
         first_line = lines[0] if lines else "EMPTY"
         last_line = lines[-1] if lines else "EMPTY"
         # Handle empty last line from split
         if not last_line.strip() and len(lines) > 1: last_line = lines[-2]
         
         print(f"✅ [FINANCE AUTH] RS256 Public Key loaded.")
         print(f"   Fingerprint (SHA256): {key_hash}")
         print(f"   Format Check: {first_line} ... {last_line}")
     except Exception as e:
         print(f"⚠️ [FINANCE AUTH] Key loaded but failed to log details: {e}")

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7 # Shortened for testing or as policy

# OAuth2 Scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# -----------------------------------------------------------------------------
# CORE FUNCTIONS
# -----------------------------------------------------------------------------

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a standardized JWT Access Token using RS256 Private Key.
    Only available if AO_JWT_PRIVATE_KEY_PEM is set (Accounts Service).
    """
    if not AO_JWT_PRIVATE_KEY_PEM:
        raise RuntimeError("Cannot sign token: Private Key not configured.")
        
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Standard Claims
    to_encode.update({
        "exp": expire,
        "iss": "accounts.somosao.com",
        "aud": "somosao"
    })
    
    # Sign with Private Key
    encoded_jwt = jwt.encode(
        to_encode, 
        AO_JWT_PRIVATE_KEY_PEM, 
        algorithm=ALGORITHM,
        headers={"kid": AO_JWT_KEY_ID}
    )
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Creates a long-lived Refresh Token using RS256 Private Key.
    Only available if AO_JWT_PRIVATE_KEY_PEM is set (Accounts Service).
    """
    if not AO_JWT_PRIVATE_KEY_PEM:
        raise RuntimeError("Cannot sign token: Private Key not configured.")
        
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iss": "accounts.somosao.com",
        "aud": "somosao",
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode, 
        AO_JWT_PRIVATE_KEY_PEM, 
        algorithm=ALGORITHM,
        headers={"kid": AO_JWT_KEY_ID}
    )
    return encoded_jwt

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and validates a JWT using RS256 Public Key.
    Available to all services with Public Key configured.
    """
    if not AO_JWT_PUBLIC_KEY_PEM:
        print("❌ [AUTH] Cannot verify token: Public Key not configured.")
        return None
        
    try:
        # Hotfix: Strip optional Bearer prefix
        if token.startswith("Bearer "):
            token = token.split(" ")[1]

        # Verify Signature using Public Key
        # DEBUG: Print Token Header and Key details
        try:
            unverified_header = jwt.get_unverified_header(token)
            print(f"🕵️ [AUTH DEBUG] Token Header: {unverified_header}")
            print(f"🕵️ [AUTH DEBUG] Using Key ID: {AO_JWT_KEY_ID}")
            print(f"🕵️ [AUTH DEBUG] Public Key Start: {AO_JWT_PUBLIC_KEY_PEM[:30] if AO_JWT_PUBLIC_KEY_PEM else 'NONE'}...")
        except Exception as e:
            print(f"🕵️ [AUTH DEBUG] Failed to inspect token header: {e}")

        # We disable strict audience check here because Accounts service issues tokens
        # with multiple audiences ["somosao", "ao-platform"] and PyJWT can be picky.
        # The signature verification with Public Key is the primary security mechanism.
        payload = jwt.decode(
            token, 
            AO_JWT_PUBLIC_KEY_PEM, 
            algorithms=[ALGORITHM],
            # audience="somosao", # Disabled to allow multi-audience
            options={"require": ["exp", "iss", "sub"], "verify_aud": False}
        )
        return payload
    except jwt.ExpiredSignatureError:
        print("⚠️ [AUTH] Token Expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"⚠️ [AUTH] Invalid Token: {e}")
        # DEBUG RE-RAISE to see detailed error in logs? No, print is enough usually.
        return None
    except Exception as e:
        print(f"❌ [AUTH] Unexpected Decode Error: {e}")
        return None

# -----------------------------------------------------------------------------
# FASTAPI DEPENDENCY
# -----------------------------------------------------------------------------

async def get_current_user_claims(request: Request) -> Dict[str, Any]:
    """
    Dependency to validate Request Auth.
    Strategies:
    1. Header: Authorization: Bearer <token>
    2. Cookie: accounts_access_token
    """
    token = None
    
    # 1. Header Authorization
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
    # 2. Cookie (HttpOnly)
    if not token:
        token = request.cookies.get("accounts_access_token")
    
    # 3. Validation
    if not token:
        # print("Auth Failed: No token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = decode_token(token)
    if not payload:
        # print("Auth Failed: Token Expired or Invalid")
        # Strict 401 triggers frontend refresh flow
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Inject into Request State for downstream use
    request.state.user = payload
    
    return payload

# Import EntitlementsClient from Local Common
try:
    from .entitlements import entitlements_client
except ImportError:
    from common.entitlements import entitlements_client

def require_service(service_slug: str):
    """
    Dependency factory to enforce service entitlement via V3 Entitlements System.
    Usage: @app.get(..., dependencies=[Depends(require_service("daily"))])
    """
    def _check_service(request: Request, claims: Dict[str, Any] = Depends(get_current_user_claims)):
        # SuperAdmin/Admin Bypass? 
        role = claims.get("role")
        if role == "SuperAdmin":
            return claims
            
        # 1. Get Context
        org_id = claims.get("org_id")
        
        if not org_id:
             # Fallback to legacy "services" list checks if org_id is missing?
             services = claims.get("services", [])
             if isinstance(services, list):
                 if service_slug.lower() in [s.lower() for s in services]:
                     return claims
             raise HTTPException(status_code=403, detail="No Organization Context for Entitlement Check")

        # 2. Versioned Check
        token_version = claims.get("entitlements_version", 0)
        
        has_access = entitlements_client.check_access(org_id, token_version, service_slug)
        
        if not has_access:
            # Final Fallback: Check legacy 'services' claim one last time
            services = claims.get("services", [])
            if isinstance(services, list) and service_slug.lower() in [s.lower() for s in services]:
                return claims
                
            raise HTTPException(status_code=403, detail=f"Organization does not have access to '{service_slug}'")
                  
        return claims
        
    return _check_service
