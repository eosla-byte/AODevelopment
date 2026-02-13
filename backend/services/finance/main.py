from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import os
import sys
import datetime
import requests
from typing import Optional

# Path Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from common.auth import create_access_token, decode_token
from common.database import get_db

# Import Routers
# Using absolute imports based on sys.path hack
from routers import projects, hr, expenses, quotes

app = FastAPI(title="AO Finance & Operations")

import logging
logger = logging.getLogger("uvicorn")
logger.info("[FINANCE V2 CHECK] Service Starting with V2 Codebase...")


# CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Auth Middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
            
        path = request.url.path
        
        # Public Paths
        public_paths = ["/", "/login", "/health", "/version_check", "/logout", "/favicon.ico"]
        if path in public_paths or path.startswith("/static") or path.startswith("/assets") or path.startswith("/debug"):
            return await call_next(request)
            
        # Token Check
        token = request.cookies.get("accounts_access_token")
        if not token: token = request.cookies.get("access_token") 
        
        if not token:
            # Check Header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                
        # API vs Web
            if path.startswith("/api"):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            return RedirectResponse("/", status_code=303)
            
        # Verify Token
        from common.auth import decode_token
        
        # DEBUG: Log raw token extract
        # logger.info(f"🕵️ [MIDDLEWARE] Verifying token: {token[:10]}...{token[-10:]}")
        print(f"🕵️ [MIDDLEWARE] Verifying token: {token[:10]}...{token[-10:]}")

        payload = decode_token(token)
        if not payload:
             print("⛔ [MIDDLEWARE] Token invalid -> Redirecting")
             if path.startswith("/api"):
                return JSONResponse({"error": "Invalid Token"}, status_code=401)
             return RedirectResponse("/", status_code=303)
             
        request.state.user = payload
        return await call_next(request)

app.add_middleware(AuthMiddleware)

# Include Routers
app.include_router(projects.router)
app.include_router(hr.router)
app.include_router(expenses.router)
app.include_router(quotes.router)

import requests
from fastapi import Form

# ... (imports)

@app.post("/ao-login-auth")
async def login_proxy(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Proxies login request to Accounts Service (Monolith) to get valid Cookies.
    Finance Service cannot issue RS256 tokens itself (no Private Key).
    """
    # Public URL of Accounts Service
    ACCOUNTS_URL = "https://accounts.somosao.com/auth/login"
    
    try:
        # Send Form Data (as Accounts expects 'email', we map 'username' -> 'email')
        resp = requests.post(
            ACCOUNTS_URL, 
            data={"email": username, "password": password}, 
            allow_redirects=False,
            timeout=10
        )
        
        if resp.status_code == 200:
            # Success!
            # Accounts returns JSON: {"status": "ok", "redirect": "...", ...}
            # We redirect user to Dashboard
            target_url = "/projects"
            
            response = RedirectResponse(target_url, status_code=303)
            
            # Forward Cookies from Accounts Response
            # requests.cookies is a CookieJar. We iterate usage.
            logger.info(f"🕵️ [LOGIN PROXY] Received {len(resp.cookies)} cookies from Accounts")
            for cookie in resp.cookies:
                logger.info(f"   🍪 {cookie.name} len={len(cookie.value)}")
                if cookie.name == "accounts_access_token":
                     parts = cookie.value.split('.')
                     if len(parts) == 3:
                         logger.info(f"      Signature: {parts[2]}")
                
                # We blindly copy values. 
                # Note: 'domain' might need adjustment if it's strict, but .somosao.com is fine.
                response.set_cookie(
                    key=cookie.name,
                    value=cookie.value,
                    domain=cookie.domain,
                    path=cookie.path,
                    secure=cookie.secure,
                    httponly=cookie.has_nonstandard_attr('HttpOnly') or True, # Default to True for auth tokens
                    samesite='Lax' # Safe default
                )
            
            return response
        else:
            # Failed (401, 403, etc)
            print(f"Login Proxy Failed: {resp.status_code} - {resp.text}")
            return RedirectResponse("/?error=invalid_credentials", status_code=303)
            
    except Exception as e:
        print(f"Login Proxy System Error: {e}")
        return RedirectResponse("/?error=system_error", status_code=303)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Landing / Login Logic
    
    # 1. Check if authenticated
    token = request.cookies.get("accounts_access_token")
    if not token: token = request.cookies.get("access_token")
    
    is_authenticated = False
    if token:
        from common.auth import decode_token
        if decode_token(token):
            is_authenticated = True
            
    if is_authenticated:
        # Redirect to Dashboard/Projects
        return RedirectResponse("/projects", status_code=303)
        
    # 2. Not Authenticated -> Show Login
    # We use the generic login template.
    return templates.TemplateResponse("login.html", {"request": request, "service_name": "Finance & Ops"})


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "finance"}

@app.get("/logout")
async def logout():
    return RedirectResponse("/logout-force", status_code=303)

@app.get("/logout-force")
async def logout_force():
    """
    Aggressively clears all auth cookies to fix 'Stuck Token' issues.
    """
    response = HTMLResponse(content="<h1>Logged Out</h1><p>Cookies cleared. <a href='/'>Return to Login</a></p>")
    
    domains = [None, ".somosao.com", "somosao.com", "finance.somosao.com"]
    cookies = ["accounts_access_token", "access_token", "accounts_refresh_token"]
    
    for cookie_name in cookies:
        for domain in domains:
            response.delete_cookie(key=cookie_name, domain=domain, path="/")
            response.delete_cookie(key=cookie_name, domain=domain, path="/api")
            
    return response

@app.get("/version_check")
def version_check():
    return {"service": "AO Finance", "version": "v2.0-migrated"}

@app.get("/debug/auth-config")
def debug_auth_config():
    """
    Diagnostic endpoint to verify loaded keys and algorithms.
    """
    import hashlib
    from common.auth import AO_JWT_PUBLIC_KEY_PEM, ALGORITHM
    
    fp = "MISSING"
    if AO_JWT_PUBLIC_KEY_PEM:
        try:
            fp = hashlib.sha256(AO_JWT_PUBLIC_KEY_PEM).hexdigest()[:16]
        except Exception as e:
            fp = f"ERROR: {e}"
            
    return {
        "service": "finance",
        "algorithm": ALGORITHM,
        "public_key_fingerprint": fp,
        "pem_preview": AO_JWT_PUBLIC_KEY_PEM[:30].decode('utf-8') if AO_JWT_PUBLIC_KEY_PEM else None
    }

@app.get("/debug/verify-cookie")
def debug_verify_cookie(request: Request):
    """
    Captures the cookie and attempts detailed verification logging.
    """
    import jwt
    import traceback
    from common.auth import AO_JWT_PUBLIC_KEY_PEM, ALGORITHM
    
    token = request.cookies.get("accounts_access_token") or request.cookies.get("access_token")
    if not token:
        return {"result": "MISSING_COOKIE", "details": "No token found in cookies"}
        
    result = {
        "token_preview": f"{token[:15]}...{token[-15:]}",
        "token_length": len(token),
        "header": "FAILED_TO_PARSE",
        "key_fingerprint": "MISSING",
        "verification_result": "UNKNOWN",
        "error": None
    }
    
    # 1. Inspect Key
    if AO_JWT_PUBLIC_KEY_PEM:
        import hashlib
        result["key_fingerprint"] = hashlib.sha256(AO_JWT_PUBLIC_KEY_PEM).hexdigest()[:16]
        
    # 2. Inspect Header
    try:
        result["header"] = jwt.get_unverified_header(token)
    except Exception as e:
        result["header_error"] = str(e)
        
    # 3. Inspect Payload (Unverified)
    try:
        result["unverified_payload"] = jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        result["payload_error"] = str(e)
        
    # 4. Verify Signature
    try:
        jwt.decode(
            token,
            AO_JWT_PUBLIC_KEY_PEM,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iss", "sub"], "verify_aud": False}
        )
        result["verification_result"] = "SUCCESS"
    except Exception as e:
        result["verification_result"] = "FAILED"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        # result["traceback"] = traceback.format_exc()
        
    return result

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
