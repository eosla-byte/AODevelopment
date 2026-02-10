
import os
import jwt
import datetime
from datetime import timedelta
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict, Any

# -----------------------------------------------------------------------------
# CONFIGURATION (RS256 Strict)
# -----------------------------------------------------------------------------
# Keys: AO_JWT_PRIVATE_KEY_PEM / AO_JWT_PUBLIC_KEY_PEM
# Exact names required.

print("✅ [AUTH] Loading ROOT auth.py")

def load_key_strict(env_name, required=False):
    val = os.getenv(env_name)
    if not val:
        if required:
            raise ValueError(f"❌ [AUTH] CRITICAL ERROR: Environment variable '{env_name}' is missing.")
        return None
    
    # Secure Log (Length only)
    print(f"✅ [AUTH] Loaded {env_name} (Length: {len(val)})")
    
    # Handle Newline Escaping
    return val.strip().replace("\\n", "\n").encode('utf-8')

# Load Keys
try:
    # Strict loading for Accounts (Private) and Verification (Public)
    AO_JWT_PRIVATE_KEY_PEM = load_key_strict("AO_JWT_PRIVATE_KEY_PEM", required=False)
    AO_JWT_PUBLIC_KEY_PEM = load_key_strict("AO_JWT_PUBLIC_KEY_PEM", required=False)
    
except Exception as e:
    print(f"❌ [AUTH] Configuration Error: {e}")
    raise e

AO_JWT_KEY_ID = os.getenv("AO_JWT_KEY_ID", "ao-k1")

# Check Validity for specific roles (Signing vs Verifying) happen at runtime or service startup.


ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7 # Shortened for testing or as policy

# OAuth2 Scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# -----------------------------------------------------------------------------
# CORE FUNCTIONS
# -----------------------------------------------------------------------------

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None, audience: str = "somosao") -> str:
    """
    Creates a standardized JWT Access Token using RS256 Private Key.
    Only available if AO_JWT_PRIVATE_KEY_PEM is set (Accounts Service).
    """
    if not AO_JWT_PRIVATE_KEY_PEM:
        raise RuntimeError("❌ [AUTH] Signing Failed: AO_JWT_PRIVATE_KEY_PEM is missing.")
        
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Standard Claims
    to_encode.update({
        "exp": expire,
        "iss": "accounts.somosao.com",
        "aud": audience
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
        raise RuntimeError("❌ [AUTH] Signing Failed: AO_JWT_PRIVATE_KEY_PEM is missing.")
        
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

def decode_token(token: str, audience: str = "somosao") -> Optional[Dict[str, Any]]:
    """
    Decodes and validates a JWT using RS256 Public Key.
    Available to all services with Public Key configured.
    """
    if not AO_JWT_PUBLIC_KEY_PEM:
        print("❌ [AUTH] Verification Failed: AO_JWT_PUBLIC_KEY_PEM is missing.")
        return None
        
    try:
        # Hotfix: Strip optional Bearer prefix
        if token.startswith("Bearer "):
            token = token.split(" ")[1]

        # Verify Signature using Public Key
        payload = jwt.decode(
            token, 
            AO_JWT_PUBLIC_KEY_PEM, 
            algorithms=[ALGORITHM],
            audience=audience,
            issuer="accounts.somosao.com",
            options={"require": ["exp", "iss", "aud", "sub"]}
        )
        return payload
    except jwt.ExpiredSignatureError:
        print("⚠️ [AUTH] Token Expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"⚠️ [AUTH] Invalid Token: {e}")
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
        
    # 2. Cookie (HttpOnly) - Unified check
    if not token:
        token = request.cookies.get("accounts_access_token")
    if not token:
        token = request.cookies.get("access_token")
    
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

def require_service(service_slug: str):
    """
    Dependency factory to enforce service entitlement.
    Usage: @app.get(..., dependencies=[Depends(require_service("daily"))])
    """
    def _check_service(request: Request, claims: Dict[str, Any] = Depends(get_current_user_claims)):
        # SuperAdmin/Admin Bypass
        role = claims.get("role")
        if role in ["SuperAdmin", "Admin"]:
            return True
            
        services = claims.get("services", [])
        
        # Check if service is enabled
        # Normalize? slugs should be lowercase in claims
        if service_slug not in services:
             # print(f"⛔ [Auth] Access Denied: User {claims.get('sub')} lacks '{service_slug}' entitlement.")
             raise HTTPException(status_code=403, detail="service_not_enabled")
        return claims
        
    return _check_service
