
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
import re

def load_pem_key(env_var_name, is_private=False):
    val = os.getenv(env_var_name)
    if not val: return None
    
    # 1. Sanitize: Remove wrapping quotes and whitespace
    val = val.strip().strip("'").strip('"')
    
    # 2. Normalize Newlines: 
    # Handle literal escaped \n, \r\n, \r
    val = val.replace("\\n", "\n").replace("\\r", "")
    
    # 3. Aggressive Normalization via Split/Join
    # distinct lines, removing empties
    lines = [line.strip() for line in val.split("\n") if line.strip()]
    
    # 4. Reconstruct PEM
    # Ensure Header and Footer are correct
    # We support both PKCS#1 (RSA PUBLIC KEY) and PKCS#8 (PUBLIC KEY)
    
    clean_lines = []
    found_header = False
    found_footer = False
    
    for line in lines:
        # Flexible Header Check
        if "BEGIN" in line and "KEY" in line:
            clean_lines.append(line) # Use line as is
            found_header = True
        elif "END" in line and "KEY" in line:
            clean_lines.append(line)
            found_footer = True
        else:
            # Body lines - strict alphanum check? No, just base64 chars
            # Ideally we only take valid b64 lines, but trusting split() is usually ok
            clean_lines.append(line)
            
    if not found_header or not found_footer:
        # Fallback: validation check
        # Sometimes keys are pasted WITHOUT headers. We can try to guess?
        # For now, strict on having headers involves user copy-paste correctness.
        print(f"❌ [AUTH] Malformed PEM in {env_var_name}. Looking for BEGIN/END lines.")
        # Attempt to auto-wrap?
        # if len(lines) > 1 and not found_header: ...
        
        # Fail Fast
        raise ValueError(f"CRITICAL: Invalid PEM structure in {env_var_name}")

    # Final String
    pem_str = "\n".join(clean_lines) + "\n"
    
    return pem_str.encode('utf-8')

try:
    AO_JWT_PRIVATE_KEY_PEM = load_pem_key("AO_JWT_PRIVATE_KEY_PEM", is_private=True)
    AO_JWT_PUBLIC_KEY_PEM = load_pem_key("AO_JWT_PUBLIC_KEY_PEM", is_private=False)
except Exception as e:
    print(f"🔥 [STARTUP FATAL] Auth Configuration Error: {e}")
    # We should probably exit or let it crash, but printing is good for logs.
    AO_JWT_PRIVATE_KEY_PEM = None
    AO_JWT_PUBLIC_KEY_PEM = None
    raise e

AO_JWT_KEY_ID = os.getenv("AO_JWT_KEY_ID", "ao-k1")

# LOGGING: Safe Fingerprint
if AO_JWT_PUBLIC_KEY_PEM:
     try:
         # SHA256 Fingerprint
         key_hash = hashlib.sha256(AO_JWT_PUBLIC_KEY_PEM).hexdigest()[:16]
         
         # Line Analysis
         pem_decoded = AO_JWT_PUBLIC_KEY_PEM.decode('utf-8')
         lines = pem_decoded.strip().split('\n')
         total_lines = len(lines)
         first_line = lines[0]
         second_line = lines[1][:10] + "..." if total_lines > 1 else "N/A"
         last_line = lines[-1]
         
         print(f"✅ [FINANCE AUTH] RS256 Public Key Loaded Successfully.")
         print(f"   Fingerprint (SHA256): {key_hash}")
         print(f"   Lines: {total_lines}")
         print(f"   Structure: {first_line}")
         print(f"              {second_line}")
         print(f"              {last_line}")
         
     except Exception as e:
         print(f"⚠️ [FINANCE AUTH] Key loaded but failed to log details: {e}")

if not AO_JWT_PRIVATE_KEY_PEM and not AO_JWT_PUBLIC_KEY_PEM:
     print("⚠️ [AUTH] RS256 Keys missing! Authentication WILL FAIL.")

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

        # DEBUG: Print Token Header and Key details
        try:
            # print(f"🕵️ [AUTH DEBUG] Token Length: {len(token)}") 
            # Use Logger if possible, but print is standard here.
            
            # Verify using the Key Bytes directly
            # RELAXED AUDIENCE CHECK: We allow 'somosao', 'ao-platform', or list.
            # actually, let's allow ANY audience for now to rule it out, 
            # OR explicitly match what Accounts issues (['somosao', 'ao-platform'])
            
            payload = jwt.decode(
                token, 
                AO_JWT_PUBLIC_KEY_PEM, # Pass bytes directly
                algorithms=[ALGORITHM],
                # options={"require": ["exp", "iss", "sub"], "verify_aud": False} # DEBUG: Disable Aud check completely
                audience=["somosao", "ao-platform"], # Expect list match
                options={"verify_aud": False} # CRITICAL DEBUG: Disable audience check to isolate Signature Error
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            print("⚠️ [AUTH] Token Expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"⚠️ [AUTH] Invalid Token: {e}")
            # DEEP DEBUG
            try:
                unverified = jwt.decode(token, options={"verify_signature": False})
                print(f"   🔍 Unverified Payload: {unverified}")
                print(f"   🔍 Unverified Header: {jwt.get_unverified_header(token)}")
            except:
                pass
            return None
        except Exception as e:
            print(f"❌ [AUTH] Unexpected Decode Error: {e}")
            return None
    except Exception as e:
         print(f"❌ [AUTH] Global Decode Error: {e}")
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
