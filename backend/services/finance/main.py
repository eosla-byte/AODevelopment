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
        if path in public_paths or path.startswith("/static") or path.startswith("/assets"):
            return await call_next(request)
            
        # Token Check
        token = request.cookies.get("accounts_access_token")
        if not token: token = request.cookies.get("access_token") 
        
        if not token:
            # Check Header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                
        if not token:
            # API vs Web
            if path.startswith("/api"):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            return RedirectResponse("/", status_code=303)
            
        # Verify Token
        from common.auth import decode_token
        
        payload = decode_token(token)
        if not payload:
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
            for cookie in resp.cookies:
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
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("accounts_access_token")
    response.delete_cookie("access_token")
    return response

@app.get("/version_check")
def version_check():
    return {"service": "AO Finance", "version": "v2.0-migrated"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
