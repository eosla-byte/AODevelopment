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
logger.info("[FINANCE V3.2 MIDDLEWARE FIX] Service Starting with Whitelisted Login Route...")

# ENSURE TABLES EXIST IN OPS DB
# This is required because Finance Service manages its own extension tables in db-operations (postgres-x8en)
# and migrations might not be running against this specific DB.
try:
    from common.database import engine_ops, Base
    logger.info("🔧 [STARTUP] Verifying/Creating tables in Operations DB...")
    Base.metadata.create_all(bind=engine_ops)
    logger.info("✅ [STARTUP] Operations DB Schema Verified.")
except Exception as e:
    logger.error(f"❌ [STARTUP] Failed to create tables in Ops DB: {e}")


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
        public_paths = ["/", "/login", "/health", "/version_check", "/logout", "/favicon.ico", "/ao-login-auth"]
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

        # Fallback to Host-Only Cookie (finance_auth_token)
        if not token:
            token = request.cookies.get("finance_auth_token")
                
        # API vs Web
        if not token:
            if path.startswith("/api"):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            return RedirectResponse("/", status_code=303)
            
        # Verify Token
        from common.auth import decode_token
        
        # DEBUG: Log raw token extract
        # logger.info(f"🕵️ [MIDDLEWARE] Verifying token: {token[:10]}...{token[-10:]}")
        # print(f"🕵️ [MIDDLEWARE] Verifying token: {token[:10]}...{token[-10:]}")

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
                
                # FORCE DOMAIN to .somosao.com to ensure shared auth works
                # We ignore the domain sent by Accounts (which might be accounts.somosao.com or None)
                target_domain = ".somosao.com"
                
                # Force Secure/SameSite=Lax for top-level navigation stability
                # None is for iframes, but can be finicky. Lax is robust for main window.
                
                # 1. Primary Shared Cookie (.somosao.com)
                response.set_cookie(
                    key=cookie.name,
                    value=cookie.value,
                    domain=target_domain, 
                    path="/", 
                    secure=True, 
                    httponly=True, 
                    samesite='Lax' 
                )

                # 2. Fallback Host-Only Cookie (No Domain)
                # This guarantees the browser stores it for finance.somosao.com even if wildcard fails
                if cookie.name == "accounts_access_token":
                    logger.info(f"   🍪 Setting Fallback Cookie: finance_auth_token (Host-Only)")
                    response.set_cookie(
                        key="finance_auth_token",
                        value=cookie.value,
                        # domain=None, # Defaults to Host-Only
                        path="/",
                        secure=True,
                        httponly=True,
                        samesite='Lax'
                    )
            
            return response
        else:
            # Failed (401, 403, etc)
            logger.error(f"❌ [LOGIN PROXY] Failed: Status={resp.status_code} Body={resp.text[:200]}")
            return RedirectResponse("/?error=invalid_credentials", status_code=303)
            
    except Exception as e:
        logger.error(f"🔥 [LOGIN PROXY] System Error: {e}")
        return RedirectResponse("/?error=system_error", status_code=303)

# --- Dashboard Logic ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # 1. Auth Check
    token = request.cookies.get("accounts_access_token")
    if not token: token = request.cookies.get("finance_auth_token")
    if not token: token = request.cookies.get("access_token")
    
    is_authenticated = False
    if token:
        from common.auth import decode_token
        if decode_token(token):
             is_authenticated = True
             
    if not is_authenticated:
        return templates.TemplateResponse("login.html", {"request": request, "service_name": "Finance & Ops"})
        
    # 2. Fetch Data for Dashboard
    from common.database import get_projects, get_expenses_monthly, get_quotations, get_collaborators
    
    # A. Active Projects
    all_projects = get_projects()
    active_projects = [p for p in all_projects if p.status == 'Activo']
    
    # B. Financials
    # Income (Total Paid Amount on Projects)
    total_income = sum(p.paid_amount for p in all_projects if p.paid_amount)
    
    # Expenses (Total Expenses this year? Or All time? "Total pagado a la fecha")
    # We'll grab current year for now or try to sum everything if feasible. 
    # get_expenses_monthly returns data for a specific year. Let's do Current Year + Previous Year for a better scope?
    # Or just Current Year as "Year to Date". User said "a la fecha". Usually implies YTD or Total.
    # Let's stick to Current Year YTD for speed.
    current_year = datetime.datetime.now().year
    expenses_ytd = get_expenses_monthly(current_year)
    total_expenses = 0.0
    for col in expenses_ytd:
        total_expenses += sum(c['amount'] for c in col['cards'])
        
    # HR (Payroll)
    # We verify "Total pagado a la fecha" in HR. 
    # Without a historical payroll table, we can estimate YTD based on active collaborators * months passed? 
    # Or just show "Monthly Payroll" x 12?
    # Better: Sum of 'paid_amount' if we had it. 
    # For now, let's display "Planilla Mensual" as a proxy or 0.0 if not available.
    collabs = get_collaborators()
    active_collabs = [c for c in collabs if getattr(c, 'status', 'Activo') == 'Activo' and not getattr(c, 'archived', False)]
    monthly_payroll = sum(c.salary for c in active_collabs if hasattr(c, 'salary'))
    # Crude YTD Estimate: Monthly * Month of Year
    # This is rough but gives a number. 
    hr_ytd = monthly_payroll * datetime.datetime.now().month
    
    # Quotes
    quotes = get_quotations()
    total_quotes = len(quotes)
    
    # Tasks (Mock or from Project Reminders?)
    # "Tareas de la semana creadas en cronograma"
    # We can count reminders/events in recent projects?
    weekly_tasks = 0
    now = datetime.datetime.now()
    start_week = now - datetime.timedelta(days=now.weekday())
    
    # Database needs 'get_all_reminders' or we iterate projects
    for p in active_projects:
        rems = getattr(p, 'reminders', [])
        if rems:
             # Logic to count this week?
             pass

    # C. Timeline Data
    timeline_events = []
    
    for p in active_projects:
        # Project Range
        if getattr(p, 'start_date', None):
            try:
                start_val = p.start_date
                start_dt = None
                
                # Robust Date Parsing
                if isinstance(start_val, datetime.date) or isinstance(start_val, datetime.datetime):
                    start_dt = start_val
                elif isinstance(start_val, str):
                    # Try common formats
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                        try:
                            start_dt = datetime.datetime.strptime(start_val, fmt)
                            break
                        except: continue
                
                if start_dt:
                    # Start
                    timeline_events.append({
                        "id": f"start-{p.id}",
                        "title": f"Inicio: {p.client}",
                        "timestamp": start_dt.strftime("%Y-%m-%d"), 
                        "type": "milestone",
                        "color": "#3b82f6" # Blue
                    })
                    
                    # Projected End
                    # Handle duration which might be string or float
                    dur = getattr(p, 'duration_months', 0)
                    try: dur = float(dur)
                    except: dur = 0.0
                    
                    if dur > 0:
                        end_dt = start_dt + datetime.timedelta(days=int(dur * 30))
                        timeline_events.append({
                            "id": f"proj-end-{p.id}",
                            "title": f"Fin Est.: {p.client}",
                            "timestamp": end_dt.strftime("%Y-%m-%d"),
                            "type": "milestone",
                            "color": "#3b82f6" 
                        })
                        
                        # Real End (Extra Time)
                        extra = getattr(p, 'additional_time_months', 0)
                        try: extra = float(extra)
                        except: extra = 0.0
                        
                        if extra > 0:
                            real_end_dt = end_dt + datetime.timedelta(days=int(extra * 30))
                            timeline_events.append({
                                "id": f"real-end-{p.id}",
                                "title": f"Fin Real: {p.client}",
                                "timestamp": real_end_dt.strftime("%Y-%m-%d"),
                                "type": "milestone",
                                "color": "#ef4444" # Red
                            })
            except Exception as e:
                logger.error(f"Error processing timeline for project {p.id}: {e}")
                pass

        # Payments / Invoices (If we had a dedicated list, we would add them here)
        # For now, we visualize the projects themselves.
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "metrics": {
            "active_projects": len(active_projects),
            "total_income": total_income,
            "total_expenses": total_expenses,
            "hr_ytd": hr_ytd,
            "total_quotes": total_quotes,
            "weekly_tasks": 12 # Mock for now or calculate later
        },
        "timeline_events": timeline_events,
        "title": "Dashboard General"
    })

@app.get("/dashboard")
async def dashboard_alias(request: Request):
    return await dashboard(request)


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
    
    domains = [None, ".somosao.com", "somosao.com", "finance.somosao.com", "www.somosao.com"]
    cookies = ["accounts_access_token", "access_token", "accounts_refresh_token", "finance_auth_token"]
    
    # Aggressively delete everything
    for cookie_name in cookies:
        for domain in domains:
            response.delete_cookie(key=cookie_name, domain=domain, path="/")
            response.delete_cookie(key=cookie_name, domain=domain, path="/api")
            # Also try without domain (host only)
            response.delete_cookie(key=cookie_name, path="/")
            
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
