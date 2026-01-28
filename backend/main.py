
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict
import uvicorn
import os
import shutil
import json
import mimetypes
import datetime
import uuid
# Database Imports
from common.database import (
    get_projects, create_project, get_project_details, 
    get_collaborators, create_collaborator, get_collaborator_details, update_project_meta, 
    update_collaborator, update_collaborator_picture, add_adjustment, remove_adjustment, 
    calculate_isr_projection, get_months_worked, save_payroll_close, toggle_archive_collaborator, 
    update_project_profit_config, add_partner_withdrawal, update_project_file_meta, 
    get_expenses_monthly, add_expense_column, add_expense_card, copy_expense_card, delete_expense_card, 
    delete_expense_column, update_expense_card_files, add_project_reminder, delete_project_reminder, 
    toggle_project_reminder, get_total_collaborator_allocations, update_project_collaborators, 
    get_collaborator_assigned_projects, get_project_stats_by_category, delete_project_file_meta,
    update_user_assigned_projects, update_user_permissions,
    # Auth
    User, get_users, save_user, get_user_by_email, delete_user,
    # Market Study
    get_market_studies, add_market_study, delete_market_study, get_project_collaborator_count,
    # Estimations
    get_estimations, create_estimation, update_estimation, delete_estimation,
    # Quotations
    get_quotations, get_quotation_by_id, create_quotation, update_quotation, delete_quotation,
    # Templates
    get_templates, save_template
)
from common.auth_utils import get_password_hash, verify_password, create_access_token, decode_access_token
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

app = FastAPI()

@app.get("/system/force_admin_reset")
async def force_admin_reset():
    """
    Endpoint de emergencia para restaurar acceso admin en Produccion (Monolito).
    """
    try:
        # Importar User y save_user de las dependencias globales o database
        from common.database import save_user, User
        from common.auth_utils import get_password_hash
        
        admin = User(
            id="admin_01",
            name="Administrador",
            email="admin@somosao.com",
            role="admin",
            is_active=True,
            hashed_password=get_password_hash("admin123"),
            permissions={},
            assigned_projects=[]
        )
        save_user(admin)
        return "ÉXITO MONOLITO: Admin actualizado a admin@somosao.com / admin123"
    except Exception as e:
        return f"ERROR: {str(e)}"

@app.get("/version_check")
def version_check():
    return {"version": "v3_monolith_fixed", "timestamp": datetime.datetime.now().isoformat()}

# Include Plugin API
# Include Plugin API
from routers import plugin_api, plugin_cloud, ai, sheet_api, acc_manager
app.include_router(plugin_api.router)
app.include_router(plugin_cloud.router)
app.include_router(ai.router)
app.include_router(sheet_api.router)
app.include_router(acc_manager.router)

# Input Models
class LoginRequest(BaseModel):
    username: str
    password: str

class AssignProjectRequest(BaseModel):
    user_id: str
    project_ids: List[str]
    permissions: Dict[str, bool]

# CORS Config
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount Static
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

assets_path = os.path.join(BASE_DIR, "static/public_site/assets")
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="frontend_assets")
else:
    print(f"Warning: Assets directory not found at {assets_path}")

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Auth Middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Allow CORS Preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        
        # 2. Block Protected Routes
        # Implicitly allow / (landing), /assets, /static, /api, /login
        protected_prefixes = [
            "/admin", "/estimaciones", "/cotizaciones", 
            "/projects", "/project", "/calendar", "/hr", "/create_project", "/labs"
        ]
        
        is_protected = any(path.startswith(p) for p in protected_prefixes)
        
        if is_protected:
            token = request.cookies.get("access_token")
            # Fallback Header
            # Fallback Header
            auth_header = request.headers.get("Authorization")
            if not token and auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            
            # Fallback Query Param (Bulletproof for WebViews/Iframes)
            if not token:
                token = request.query_params.get("token") or request.query_params.get("access_token")

            if not token:
                # Redirect to login instead of landing if unauthorized?
                # Or just keep behavior but now query param works.
                # Redirect to login instead of landing
                return RedirectResponse("/ao-access", status_code=303) 
            
            payload = decode_access_token(token)
            if not payload:
                # If token invalid, also redirect
                # If token invalid, also redirect
                return RedirectResponse("/ao-access", status_code=303)
                
            request.state.user = payload

            # --- ROLE BASED ACCESS CONTROL ---
            role = payload.get("role")
            
            if role == "plugin_user":
                # STRICT: Plugin Users can ONLY access /cloud-quantify
                # (API routes are not in protected_prefixes so they bypass this check)
                if not path.startswith("/cloud-quantify"):
                     return HTMLResponse("<h1>Acceso Restringido</h1><p>Su usuario es exclusivo para el Plugin de Revit y herramientas vinculadas (Cloud Quantify). No tiene acceso al Panel Administrativo.</p>", status_code=403)
            
            elif role == "cliente":
                 # Clients cannot access Admin or HR
                 if path.startswith("/admin") or path.startswith("/hr") or path.startswith("/estimaciones") or path.startswith("/cotizaciones"):
                     return RedirectResponse("/projects", status_code=303)

        response = await call_next(request)
        return response

app.add_middleware(AuthMiddleware)



@app.get("/", response_class=HTMLResponse)
async def serve_landing(request: Request):
    # Host based routing
    host = request.headers.get("host", "").lower()
    
    # If accessing via accounts subdomain, serve the Accounts/Unified Login
    if "accounts." in host:
        return templates.TemplateResponse("login.html", {"request": request})

    # Default: Serve Public Landing Page
    index_path = os.path.join(BASE_DIR, "static/public_site/index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
        
    return HTMLResponse("<h1>AO Development</h1><p>Frontend not found.</p>")

@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    # Explicit login page
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/sheets/manager", response_class=HTMLResponse)
async def serve_sheet_manager(request: Request):
    return templates.TemplateResponse("sheet_manager.html", {"request": request})

@app.get("/labs/cloud-manager", response_class=HTMLResponse)
async def labs_cloud_manager(request: Request):
    return templates.TemplateResponse("labs_cloud_manager.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, view: str = "active"):
    # 1. Projects
    projects = get_projects(archived=(view == "archived"))
    
    # 2. Metrics Calculation
    
    # Income (Paid Amount of active projects? Or all projects?)
    # Usually Income is absolute.
    income = 0.0
    if projects:
        income = sum(p.paid_amount if p.paid_amount else 0.0 for p in projects)

    # Expenses
    # Assuming get_expenses_monthly returns a structure like { "months": { "2024-01": { "total": X } }, "total_global": Y }
    # Or we sum manually.
    expenses_data = get_expenses_monthly() 
    total_expenses = 0.0
    if expenses_data:
        # get_expenses_monthly returns a LIST of month dicts
        if isinstance(expenses_data, list):
            for m in expenses_data:
                total_expenses += float(m.get("total", 0.0))
        elif isinstance(expenses_data, dict) and "months" in expenses_data:
             # Fallback for alternative structure (safety)
             for m in expenses_data["months"].values():
                 total_expenses += float(m.get("total", 0.0))

    # Payroll

    # Payroll
    collabs = get_collaborators()
    payroll_monthly = 0.0
    if collabs:
        payroll_monthly = sum(c.salary for c in collabs if not c.archived and c.salary)
    
    payroll_total = payroll_monthly * 12 # Projection
    
    # Balance
    balance = income - total_expenses - payroll_total
    
    # HR Alerts
    allocations = get_total_collaborator_allocations()
    uncovered_count = 0
    if collabs and allocations:
        for c in collabs:
            if not c.archived:
                alloc = allocations.get(c.id, 0)
                if alloc < 100: 
                    uncovered_count += 1
    
    metrics = {
        "income": income,
        "expenses": total_expenses,
        "payroll_monthly": payroll_monthly,
        "payroll_total": payroll_total,
        "balance": balance,
        "uncovered_collaborators_count": uncovered_count
    }
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "projects": projects,
        "metrics": metrics,
        "view_mode": view,
        "year": datetime.datetime.now().year
    })

@app.post("/project/{project_id}/profit/update")
async def update_profit_config_route(project_id: str, request: Request):
    form = await request.form()
    
    try:
        projected = float(form.get("projected_margin", 0))
    except: projected = 0.0
    
    try:
        real = float(form.get("real_margin", 0))
    except: real = 0.0
    
    partners = {}
    for key, val in form.items():
        if key.startswith("partner_share_") and val:
            pid = key.replace("partner_share_", "")
            try: partners[pid] = float(val)
            except: pass
            
    # New Partner
    new_pid = form.get("new_partner_id")
    new_share = form.get("new_partner_share")
    if new_pid and new_share:
        try: partners[new_pid] = float(new_share)
        except: pass
        
    success = update_project_profit_config(project_id, projected, real, partners)
    if success:
        return RedirectResponse(f"/project/{project_id}", status_code=303)
    else:
        return HTMLResponse("<h1>Error updating profit configuration</h1>", status_code=500)

@app.get("/cqt-tool", response_class=HTMLResponse)
async def view_cqt_tool(request: Request):
    # Manual Auth Check to bypass Middleware caching/redirect issues
    token = request.query_params.get("token")
    if not token:
         return HTMLResponse("<h1>Error: Access Token Missing (CQT-501)</h1><p>Please update your plugin.</p>", status_code=403)
    
    payload = decode_access_token(token)
    if not payload:
         return HTMLResponse("<h1>Error: Invalid/Expired Token (CQT-502)</h1><p>Please restart Revit/Login again.</p>", status_code=403)
         
    # Check Role?
    role = payload.get("role")
    # Plugin Users and Admins allowed. Clients? Maybe not.
    # Logic in Middleware blocked clients from admin but not cloud-quantify.
    # We allow Plugin User & Admin.
    
    response = templates.TemplateResponse("cloud_quantify.html", {"request": request})
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

@app.get("/estimaciones", response_class=HTMLResponse)
async def view_estimaciones(request: Request):
    try:
        # root_path = get_root_path() # Removed
        estimations = get_estimations()
        collaborators = get_collaborators()
        return templates.TemplateResponse("estimaciones.html", {
            "request": request, 
            "estimations": estimations,
            "collaborators": collaborators
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<h1>Error loading page</h1><pre>{traceback.format_exc()}</pre>", status_code=500)

@app.post("/estimaciones/update")
async def update_estimation_route(request: Request):
    # Support both JSON and Form (for backwards compat if needed, but switching to JSON for complex edit)
    try:
        content_type = request.headers.get('content-type', '')
        if 'application/json' in content_type:
            data = await request.json()
            est_id = data.get('est_id')
            redirect_to = data.get('redirect_to', '/estimaciones')
            updates = data.get('updates', {})
        else:
            # Fallback for simple form posts (not used by new JS logic but safe to keep or remove)
            form = await request.form()
            est_id = form.get('est_id')
            redirect_to = form.get('redirect_to', '/estimaciones')
            updates = {}
            for k, v in form.items():
                if k not in ['est_id', 'redirect_to']:
                    updates[k] = v
                    
            # Should handle numeric conversion for Form data... 
            # Simplified for now assuming JSON will be the primary driver for the new modal.
            if 'amount' in updates: updates['amount'] = float(updates['amount'])
            if 'square_meters' in updates: updates['square_meters'] = float(updates['square_meters'])
            if 'duration_months' in updates: updates['duration_months'] = float(updates['duration_months'])

    except Exception as e:
        print(f"Error parsing update: {e}")
        return RedirectResponse("/estimaciones?error=parse", status_code=303)

    # root_path = get_root_path() # Removed
    
    if est_id:
        update_estimation(est_id, updates)
        
        # Recalculate Ratio
        # Check if amount/sqm changed in updates
        if 'amount' in updates or 'square_meters' in updates:
            est = next((e for e in get_estimations() if e["id"] == est_id), None)
            if est:
                amt = float(est.get("amount", 0))
                sqm = float(est.get("square_meters", 0))
                ratio = amt / sqm if sqm > 0 else 0
                update_estimation(est_id, {"ratio": ratio})

    if request.headers.get('accept') == 'application/json':
        return JSONResponse({"status": "ok"})
        
    return RedirectResponse(redirect_to, status_code=303)

# ==========================================
# QUOTATIONS ROUTES
# ==========================================

@app.get("/cotizaciones", response_class=HTMLResponse)
async def view_quotations(request: Request):
    quotations = get_quotations()
    return templates.TemplateResponse("cotizaciones_list.html", {
        "request": request,
        "quotations": quotations
    })

@app.get("/cotizaciones/new")
async def new_quotation(request: Request, template_id: Optional[str] = None, blank: Optional[str] = None):
    # Select Template Screen
    if not template_id and not blank:
         tpls = get_templates()
         list_items = [f'<a href="/cotizaciones/new?template_id={t.id}" class="flex items-center gap-3 p-4 border border-slate-200 rounded-xl hover:bg-indigo-50 border-transparent hover:border-indigo-200 transition-all group decoration-0 cursor-pointer"><span class="text-2xl">📑</span><div><div class="font-bold text-indigo-900">{t.name}</div><div class="text-xs text-indigo-400">Plantilla personalizada</div></div></a>' for t in tpls]
         
         full_html = f"""
        <html><head><script src="https://cdn.tailwindcss.com"></script><link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;700;900&display=swap" rel="stylesheet"><style>body{{font-family:'Barlow',sans-serif}} a{{text-decoration:none!important}}</style></head>
        <body class="bg-slate-100 flex items-center justify-center h-screen">
            <div class="bg-white p-8 rounded-xl shadow-xl max-w-lg w-full text-center">
                <h1 class="text-3xl font-black mb-6 text-slate-800">Nueva Cotización</h1>
                <p class="mb-6 text-slate-500">Selecciona una plantilla para comenzar:</p>
                <div class="space-y-3 mb-8 text-left max-h-[60vh] overflow-y-auto custom-scrollbar px-1">
                    <a href="/cotizaciones/new?blank=1" class="flex items-center gap-3 p-4 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors group">
                        <span class="text-2xl group-hover:scale-110 transition-transform">📄</span>
                        <div>
                            <div class="font-bold text-slate-800">Estándar (En Blanco)</div>
                            <div class="text-xs text-slate-400">Estructura básica de 5 páginas</div>
                        </div>
                    </a>
                    { "".join(list_items) }
                </div>
                <a href="/cotizaciones" class="text-slate-400 hover:text-slate-600 text-sm font-bold uppercase tracking-wider">Cancelar</a>
            </div>
        </body></html>
        """
         return HTMLResponse(full_html)

    # Create empty quotation and redirect to editor
    import uuid
    new_id = str(uuid.uuid4())
    
    initial_blocks = []
    
    if template_id:
        tpls = get_templates()
        tgt = next((t for t in tpls if str(t.id) == str(template_id)), None)
        if tgt: initial_blocks = tgt.content_json

    if not initial_blocks:
        # Define Default Blocks Structure (Mimicking PDF pages)
        # Page 1 (Cover), Page 2 (Intro), Content, Page N-1 (Terms), Page N (Back Cover)
        initial_blocks = [
            # PAGE 1: COVER (Full Bleed Config)
            { "type": "page_config", "content": { "isCover": True, "backgroundImage": "/static/img/cover_bg.png" } },
            
            { "type": "page_break", "content": "" },

            # PAGE 2: INTRO (Fixed Layout)
            { "type": "page_config", "content": { "isCover": True, "backgroundImage": "/static/img/page2_fixed.png" } },
            
            { "type": "page_break", "content": "" },

            # PAGE 3: DYNAMIC CONTENT (Services, Timeline, etc)
            { "type": "text", "content": "<h3 class='font-bold text-lg text-indigo-700 mb-2'>ALCANCE DE SERVICIOS</h3><p>Detalle de las etapas y entregables propuestos:</p>" },
            
            { "type": "page_break", "content": "" },

             # PAGE 4: TERMS
            { "type": "text", "content": "<h3 class='font-bold text-slate-800 mb-4 text-xl'>TÉRMINOS Y CONDICIONES</h3><ul class='list-disc pl-5 space-y-2 text-sm'><li>La presente oferta tiene una validez de 15 días.</li><li>Los pagos se realizarán según avance de entregables.</li><li>Cualquier cambio sustancial en el alcance requerirá una reestimación de honorarios.</li></ul>" },
            
            { "type": "page_break", "content": "" },

            # PAGE 5: BACK COVER
            { "type": "page_config", "content": { "isCover": True, "backgroundImage": "/static/img/back_bg.png" } }
        ]

    data = {
        "id": new_id,
        "title": "Nueva Cotización",
        "client_name": "",
        "status": "Borrador",
        "content_json": initial_blocks,
        "total_amount": 0.0
    }
    create_quotation(data)
    return RedirectResponse(f"/cotizaciones/{new_id}/edit", status_code=303)

@app.get("/cotizaciones/{id}/edit", response_class=HTMLResponse)
async def edit_quotation(request: Request, id: str):
    quotation = get_quotation_by_id(id)
    if not quotation:
        return RedirectResponse("/cotizaciones")
    
    # We might need collaborators for the Service Team block?
    # collaborators = get_collaborators() 
    
    return templates.TemplateResponse("cotizacion_editor.html", {
        "request": request,
        "quotation": quotation
    })

@app.post("/cotizaciones/update")
async def update_quotation_route(request: Request):
    try:
        data = await request.json()
        quot_id = data.get('id')
        updates = data.get('updates', {})
        
        updated_q = update_quotation(quot_id, updates)
        if updated_q:
            return JSONResponse({"status": "success"})
        else:
            return JSONResponse({"status": "error", "message": "Quotation not found"}, status_code=404)
    except Exception as e:
        print(f"Error saving quotation: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/cotizaciones/delete")
async def delete_quotation_route(request: Request):
    form = await request.form()
    quot_id = form.get('quot_id')
    delete_quotation(quot_id)
    return RedirectResponse("/cotizaciones", status_code=303)

@app.post("/cotizaciones/templates")
async def save_template_route(request: Request):
    try:
        data = await request.json()
        name = data.get("name")
        content = data.get("content_json")
        if not name or not content:
            return JSONResponse({"status": "error", "message": "Missing name or content"}, status_code=400)
            
        tpl = save_template(name, content)
        if tpl: return JSONResponse({"status": "success", "id": tpl})
        else: return JSONResponse({"status": "error", "message": "DB Error"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# Config Store functions moved to database.py



@app.on_event("startup")
async def startup_event():
    # root_path = get_root_path() # Removed
    # root_path = get_root_path() # Removed
    try:
        if True:
            # Check if users exist
            users = get_users()
            if not users:
                print("No users found. Creating default Administrator.")
                # Create Default Admin
                admin = User(
                    id="admin_01",
                    name="Administrador",
                    email="admin@somosao.com",
                    role="admin",
                    is_active=True,
                    hashed_password=get_password_hash("admin123"),
                    permissions={},
                    assigned_projects=[]
                )
                save_user(admin)
                print("Default Admin Created: admin@somosao.com / admin123")
    except Exception as e:
        print(f"Startup Error (Non-Critical): {e}")

# ==========================================
# AUTH ROUTES
# ==========================================


@app.get("/ao-access", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Import plugin db functions
from database import get_plugin_sessions

@app.get("/admin/plugin", response_class=HTMLResponse)
async def admin_plugin(request: Request):
    # root_path = get_root_path() # Removed
    sessions = get_plugin_sessions()
    # Sessions are already sorted by start_time desc in database.py
    # Sessions are already sorted by start_time desc in database.py
    return templates.TemplateResponse("admin_plugin.html", {"request": request, "sessions": sessions})

# --- Version Management Routes ---
from database import get_plugin_versions, create_plugin_version, delete_plugin_version

@app.get("/admin/plugin/versions", response_class=HTMLResponse)
async def admin_plugin_versions_page(request: Request):
    versions = get_plugin_versions()
    return templates.TemplateResponse("admin_plugin_versions.html", {"request": request, "versions": versions})

@app.post("/admin/plugin/versions/add")
async def create_version_route(
    request: Request,
    version_number: str = Form(...),
    changelog: str = Form(...),
    download_url: str = Form(...),
    is_mandatory: str = Form(None) # Checkbox returns value or None
):
    mandatory = True if is_mandatory else False
    create_plugin_version(version_number, changelog, download_url, mandatory)
    return RedirectResponse("/admin/plugin/versions", status_code=303)

@app.post("/admin/plugin/versions/delete")
async def delete_version_route(request: Request, version_id: int = Form(...)):
    delete_plugin_version(version_id)
    return RedirectResponse("/admin/plugin/versions", status_code=303)


# Import auth utils for password hashing (for creating users)
from auth_utils import get_password_hash
from database import get_collaborators

@app.get("/admin/plugin/users", response_class=HTMLResponse)
async def admin_plugin_users_page(request: Request):
    # root_path = get_root_path() # Removed
    all_users = get_users()
    
    # Filter OUT clients (AO Development is for internal/plugin users only)
    users = [u for u in all_users if u.role != 'cliente']
    
    # Enhanced Users Data
    # We need to link users to database logs
    from database import get_user_plugin_stats, get_collaborator_details, get_plugin_sessions
    
    sessions = get_plugin_sessions()
    
    enhanced_users = []
    for u in users:
        # 1. Get Stats (Month Hours)
        stats = get_user_plugin_stats(u.email)
        
        # 2. Determine Online Status
        # Check last heartbeat of any active session for this user
        is_online = False
        last_seen_str = "Offline"
        
        user_sessions = [s for s in sessions if getattr(s, "user_email", "") == u.email]
        if user_sessions:
            # Sort by last heartbeat descending
            user_sessions.sort(key=lambda x: getattr(x, "last_heartbeat", datetime.datetime.min), reverse=True)
            last_session = user_sessions[0]
            
            try:
                # last_heartbeat is likely a datetime object from ORM, but handle string fallback if needed
                lh = getattr(last_session, "last_heartbeat", None)
                if isinstance(lh, str):
                    lh = datetime.datetime.fromisoformat(lh)
                
                if lh:
                    # If last heartbeat was < 5 minutes ago = ONLINE
                    diff = (datetime.datetime.now() - lh).total_seconds() / 60.0
                    if diff < 5 and getattr(last_session, "is_active", False):
                        is_online = True
                        last_seen_str = "En Linea"
                    else:
                        # Format friendly relative time
                        if diff < 60:
                            last_seen_str = f"Hace {int(diff)} min"
                        elif diff < 1440:
                            last_seen_str = f"Hace {int(diff/60)} hrs"
                        else:
                            last_seen_str = lh.strftime("%d/%m")
            except Exception as e: 
                print(f"Error calulcating online status: {e}")
                pass
            
        # 3. Find Linked HR Profile ID (for the button)
        # We search collaborators by email
        collab_id = None
        all_collabs = get_collaborators()
        for c in all_collabs:
            # Case insensitive match and strip whitespace
            if c.email and u.email and c.email.lower().strip() == u.email.lower().strip():
                collab_id = c.id
                break
                
        enhanced_users.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "month_hours": stats.get("month_hours", 0.0),
            "files_count": stats.get("files_count", 0),
            "is_online": is_online,
            "last_seen": last_seen_str,
            "collab_id": collab_id,
            "permissions": getattr(u, 'permissions', {})
        })

    collaborators = get_collaborators()
    return templates.TemplateResponse("admin_plugin_users.html", {
        "request": request, 
        "users": enhanced_users,
        "collaborators": collaborators
    })

@app.post("/admin/plugin/users")
async def create_plugin_user(
    request: Request, 
    name: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...), 
    role: str = Form(...)
):
    # root_path = get_root_path() # Removed
    existing = get_user_by_email(email)
    if existing:
        return RedirectResponse("/admin/plugin/users?error=exists", status_code=303)
        
    hashed = get_password_hash(password)
    new_user = User(
        id=str(abs(hash(email))), 
        name=name,
        email=email,
        role=role,
        is_active=True,
        hashed_password=hashed
    )
    save_user(new_user)
    return RedirectResponse("/admin/plugin/users", status_code=303)

@app.post("/admin/plugin/users/{uid}/toggle")
async def toggle_plugin_user(request: Request, uid: str):
    # root_path = get_root_path() # Removed
    users = get_users()
    for u in users:
        if u.id == uid:
            u.is_active = not u.is_active
            save_user(u)
            break
    return RedirectResponse("/admin/plugin/users", status_code=303)

@app.post("/admin/plugin/users/{uid}/delete")
async def delete_plugin_user_route(request: Request, uid: str):
    delete_user(uid)
    return RedirectResponse("/admin/plugin/users", status_code=303)

@app.post("/admin/plugin/users/{uid}/update")
async def update_plugin_user_route(
    request: Request, 
    uid: str,
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    password: str = Form(None)
):
    # Find user by ID
    users = get_users()
    target_user = None
    for u in users:
        if u.id == uid:
            target_user = u
            break
            
    if target_user:
        # Update fields (Note: verify if email change affects PK in database.py save_user)
        # Assuming save_user handles updates via ORM merge or lookup
        target_user.name = name
        target_user.email = email
        target_user.role = role
        if password and password.strip():
            target_user.hashed_password = get_password_hash(password)
            
        save_user(target_user)
        
    return RedirectResponse("/admin/plugin/users", status_code=303)

@app.post("/admin/plugin/users/{uid}/permissions")
async def update_plugin_user_permissions(request: Request, uid: str):
    data = await request.json()
    perms = data.get("permissions", {})
    # uid passed in URL is likely the ID string (hash or timestamp), NOT email.
    # But database.py expects email for AppUser updates because PK is email?
    # Wait, AppUser model definition: email = Column(String, primary_key=True).
    # But in create_plugin_user: id=str(abs(hash(email))).
    # The template renders {{ u.id }}.
    # So I need to find the user by their ID, then update.
    # But get_user_by_email takes email.
    # I need `get_user_by_id`.
    
    # Quick fix: iterate all users to find ID match? Or assuming uid IS email? 
    # In template: u.id is passed.
    # Let's add get_user_by_id in database.py or doing it here.
    
    # Better: Update database.py to handle lookup by ID field I added elsewhere or just search 
    # Actually, AppUser model shows: email=PK. It DOES NOT have an 'id' column in the SQL definition shown in models.py view earlier.
    # Wait: `id = Column(String, primary_key=True)` was NOT in AppUser. 
    # `email = Column(String, primary_key=True)`
    # But `User` class wrapper has `id`.
    # `save_user` uses `id` passed to it? 
    # Let's check models.py again.
    # AppUser: email(PK), hashed_password, full_name, role, is_active. NO ID column.
    # So where is 'id' coming from? 
    # In `get_users`, `User` object is created with `u.email` as first arg? 
    # `User(u.email, u.full_name, ...)`
    # So u.id == u.email.
    # So uid passed here IS the email.
    
    from database import update_user_permissions
    update_user_permissions(uid, perms)




@app.post("/ao-login-auth")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # root_path = get_root_path() # Removed
    user = get_user_by_email(username)
    print(f"Login attempt: {username}")
    
    if not user:
        return RedirectResponse("/ao-access?error=1", status_code=303)
        
    if not verify_password(password, user.hashed_password):
        print("Invalid password")
        return RedirectResponse("/ao-access?error=1", status_code=303)
        
    if not user.is_active:
         return RedirectResponse("/ao-access?error=locked", status_code=303)

    # BLOCK PLUGIN USERS FROM WEB LOGIN
    if user.role == "plugin_user":
        # They should not be logging in via web form
        return RedirectResponse("/ao-access?error=restricted_role", status_code=303)

    # Create Token
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "name": user.name}
    )
    
    redirect_target = "/projects"
    if user.role == "admin":
        redirect_target = "/admin/users"
    elif user.role == "cliente":
        # Clients also go to projects for now (or a specific client view if strict)
        redirect_target = "/projects"
        
    response = RedirectResponse(redirect_target, status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("access_token")
    return response

# ==========================================
# ADMIN ROUTES
# ==========================================
@app.get("/admin/users", response_class=HTMLResponse)
async def read_admin_users(request: Request):
    # Verify Admin
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "admin":
        return RedirectResponse("/")
        
    # Filter: Show ONLY Admins and internal Staff (Exclude Clients and Plugin Users)
    all_users = get_users()
    users = [u for u in all_users if u.role not in ['cliente', 'plugin_user']]
    
    projects = get_projects()
    return templates.TemplateResponse("admin_users.html", {"request": request, "users": users, "projects": projects, "user": user})

@app.get("/admin/clients", response_class=HTMLResponse)
async def read_admin_clients(request: Request):
    # Verify Admin
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "admin":
        return RedirectResponse("/")
        
    # Filter IN ONLY clients for this view
    all_users = get_users()
    users = [u for u in all_users if u.role == 'cliente']
    
    projects = get_projects()
    return templates.TemplateResponse("admin_clients.html", {"request": request, "users": users, "projects": projects, "user": user})

@app.post("/admin/users/add")
async def add_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "admin":
         raise HTTPException(status_code=403, detail="Not authorized")
         
    # root_path = get_root_path() # Removed
    
    # Check exists
    if get_user_by_email(email):
        pass # Handle error? For now just ignore or overwrite
        
    new_user = User(
        id=str(int(datetime.datetime.now().timestamp())),
        name=name,
        email=email,
        role=role,
        is_active=True,
        hashed_password=get_password_hash(password)
    )
    save_user(new_user)
    
    # Redirect based on role or referer
    if role == 'cliente':
        return RedirectResponse("/admin/clients", status_code=303)
        
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/users/delete")
async def delete_user_route(request: Request, user_id: str = Form(...)):
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "admin":
         return RedirectResponse("/")
    
    # root_path = get_root_path() # Removed
    # Prevent self delete
    # (Simplified check)
    delete_user(user_id)
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/users/update")
async def update_user(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    role: str = Form(...),
    password: str = Form(None)
):
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "admin":
         return RedirectResponse("/")
         
    # root_path = get_root_path() # Removed
    existing = get_user_by_email(email)
    if existing:
        # Update fields
        existing.name = name
        existing.role = role
        if password and password.strip():
            existing.hashed_password = get_password_hash(password)
            
        save_user(existing)
        
    return RedirectResponse("/admin/users", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, view: str = ""):
    # Security Check
    user = getattr(request.state, "user", None)
    if not user:
        return RedirectResponse("/login")
    
    # Validation
    db_status = True
    
    # Get Data
    all_projects = get_projects() if db_status else []
    collaborators = get_collaborators() if db_status else []
    
    current_year = datetime.datetime.now().year
    expenses_data = get_expenses_monthly(current_year) if db_status else []
    
    # Calculate totals for dashboard view if needed
    for col in expenses_data:
        col['total'] = sum(c['amount'] for c in col['cards'])
    
    current_year = datetime.datetime.now().year
    
    # Filter Projects based on View
    filtered_projects = []
    if view == 'archived':
        filtered_projects = [p for p in all_projects if getattr(p, 'archived', False)]
    else:
        # Show Active/Pausa/Cerrado but NOT archived
        filtered_projects = [p for p in all_projects if not getattr(p, 'archived', False)]

    # 1. Total Active Income (Collected Amount from Active/Paused Projects)
    total_active_income = 0.0
    active_projects_count = 0
    
    for p in all_projects: # Use ALL projects for financial stats? Or just active? 
         # User said "Ingresos Totales Activos". Sticky point.
         # Let's keep logic: Activo/Pausa.
         # Whether archived or not? Probably archived ones shouldn't count towards "Active Income".
         if not getattr(p, 'archived', False) and p.status in ["Activo", "Pausa"]:
             total_active_income += p.paid_amount 
             active_projects_count += 1
    
    # 2. Total Expenses (Gastos Tab)
    total_expenses_cards = 0.0
    for col in expenses_data:
        # col is a DICT now from get_expenses_monthly
        for card in col['cards']:
             total_expenses_cards += card['amount']
            
    # 3. Total Payroll (Planilla)
    total_payroll_spent = 0.0
    
    effective_payroll_monthly = 0.0
    
    for c in collaborators:
        if not getattr(c, 'archived', False): 
            if getattr(c, 'status', 'Activo') == 'Activo':
                effective_payroll_monthly += c.base_salary + c.bonus_incentive
            
            months = get_months_worked(c.start_date)
            total_payroll_spent += months * (c.base_salary + c.bonus_incentive)
            
    # 4. General Balance
    balance = total_active_income - total_expenses_cards - total_payroll_spent

    # 5. HR Alerts (Uncovered Collabs)
    allocations = get_total_collaborator_allocations()
    collab_list = get_collaborators()
    uncovered_count = 0
    for c in collab_list:
        if c.status == "Activo":
            pct = allocations.get(c.id, 0.0)
            if pct < 100:
                uncovered_count += 1

    return templates.TemplateResponse("index.html", {
        "request": request,
        "projects": filtered_projects,
        "view_mode": view,
        "root_path": "", # Removed
        "year": current_year,
        "db_status": db_status,
        "active_projects_count": active_projects_count,
        "metrics": {
            "income": total_active_income,
            "expenses": total_expenses_cards,
            "payroll_monthly": effective_payroll_monthly,
            "payroll_total": total_payroll_spent,
            "balance": balance,
            "uncovered_collaborators_count": uncovered_count
        }
    })

@app.get("/projects", response_class=HTMLResponse)
async def read_projects(request: Request):
    # root_path = get_root_path() # Removed
    projects = get_projects()
    
    # --- Project Grouping Logic ---
    grouped_items = []
    
    # 1. Bucketize
    groups = {} 
    singles = []
    
    # Groupable Logic: ID must contain '-' AND prefix length >= 3
    # Actually user said: "first 3 letters of code... e.g. SYN-01 groups by SYN"
    # So we take prefix before '-'.
    
    for p in projects:
        # Check if project has a dash format like XXX-000
        if '-' in str(p.id):
            parts = str(p.id).split('-')
            prefix = parts[0]
            if len(prefix) >= 3:
                # Add to bucket
                if prefix not in groups:
                    groups[prefix] = []
                groups[prefix].append(p)
                continue
        
        # If no Dash or short prefix, it's single
        singles.append(p)
        
    # 2. Process Buckets
    for prefix, proj_list in groups.items():
        if len(proj_list) > 1:
            # Create a Group Object summary
            # Sort by ID or Start Date? ID usually implies order.
            proj_list.sort(key=lambda x: x.id)
            
            # Sums
            total_amount = sum(x.amount for x in proj_list if x.amount)
            total_paid = sum(x.paid_amount for x in proj_list if x.paid_amount)
            total_sqm = sum(x.square_meters for x in proj_list if x.square_meters)
            
            group_obj = {
                "is_group": True,
                "prefix": prefix,
                "name": f"Proyectos {prefix}",
                "count": len(proj_list),
                "amount": total_amount,
                "paid_amount": total_paid,
                "square_meters": total_sqm,
                "children": proj_list,
                "status": "Varios", # Mixed
                "start_date": proj_list[0].start_date # Earliest
            }
            grouped_items.append(group_obj)
        else:
            # Only 1 item, treat as single
            singles.append(proj_list[0])
            
    # 3. sorting
    # We want a unified list of [GroupObj, SingleProj, GroupObj...]
    # Sort Singles and Groups together by something... Name? ID? Status?
    # Let's keep Singles separate? Or mix them?
    # User said "Agrupar...". Implicitly shown in same list.
    
    # Add singles to list
    grouped_items.extend(singles)
    
    # Optional: Sort huge list by Name
    # grouped_items.sort(key=lambda x: x.name if hasattr(x, 'name') else x['name'])
    # Actually, recent might be better. Let's rely on insertion order or sort by date.
    
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "items": grouped_items # Renamed 'projects' to 'items' to imply mixed types
    })

@app.get("/calendar", response_class=HTMLResponse)
async def read_global_calendar(request: Request):
    # root_path = get_root_path() # Removed
    projects = get_projects()
    # Validate root logic inside get_projects handles empty/errors by returning list
    
    return templates.TemplateResponse("calendar.html", {
        "request": request, 
        "projects": projects,
        "current_month_name": datetime.datetime.now().strftime("%B")
    })

@app.get("/cotizador", response_class=HTMLResponse)
async def read_cotizador(request: Request):
    try:
        # root_path = get_root_path() # Removed
        projects = get_projects()
        
        # New: Market Studies
        market_studies = get_market_studies()
        
        # Enhanced Projects for Cotizador (Collab Count)
        for p in projects:
            # Use assigned_collaborators from Project model directly
            # Ensure we handle potential None values safely
            assigned = getattr(p, 'assigned_collaborators', {})
            if not isinstance(assigned, dict): assigned = {}
            p.collab_count = len(assigned)
            
            # Ensure numeric fields are safe for template math
            if p.amount is None: p.amount = 0.0
            if p.paid_amount is None: p.paid_amount = 0.0
            if p.square_meters is None: p.square_meters = 0.0
            if p.duration_months is None: p.duration_months = 0.0
            if p.additional_time_months is None: p.additional_time_months = 0.0
            if p.real_profit_margin is None: p.real_profit_margin = 0.0
            
        return templates.TemplateResponse("cotizador.html", {
            "request": request,
            "projects": projects,
            "market_studies": market_studies
        })
    except Exception as e:
        import traceback
        return HTMLResponse(content=f"""
        <html>
            <body style="background:#111; color:#f88; font-family:monospace; padding:20px;">
                <h1>500 Internal Server Error</h1>
                <h2>{e}</h2>
                <pre>{traceback.format_exc()}</pre>
            </body>
        </html>
        """, status_code=500)


@app.get("/project/{project_id}", response_class=HTMLResponse)
async def read_project(request: Request, project_id: str):
    # root_path = get_root_path() # Removed
    try:
        project = get_project_details(project_id)
        if not project:
            return RedirectResponse("/")
            
        return templates.TemplateResponse("project_detail.html", {
            "request": request,
            "p": project,
            "collaborators": get_collaborators(),
            "total_allocations": get_total_collaborator_allocations()
        })
    except Exception as e:
        import traceback
        return HTMLResponse(content=f"""
        <html>
            <body style="background:#111; color:#f88; font-family:monospace; padding:20px;">
                <h1>500 Internal Server Error (Debug Mode)</h1>
                <h2>{e}</h2>
                <pre>{traceback.format_exc()}</pre>
            </body>
        </html>
        """, status_code=500)

@app.post("/project/{project_id}/edit")
async def edit_project(
    project_id: str, 
    client: str = Form(""), 
    status: str = Form("Activo"),
    nit: str = Form(""),
    legal_name: str = Form(""),
    po_number: str = Form(""),
    amount: float = Form(0.0),
    emoji: str = Form("📁"),
    start_date: str = Form(""),
    duration_months: float = Form(0.0),
    additional_time_months: float = Form(0.0),
    paid_amount: float = Form(0.0),
    square_meters: float = Form(0.0),
    category: str = Form("Residencial"),
    # ACC Fields
    acc_hub: str = Form(""),
    acc_project: str = Form(""),
    acc_folder: str = Form(""),
    acc_file: str = Form("")
):
    # root_path = get_root_path() # Removed
    project = get_project_details(project_id)
    if project:
        acc_config = {
            "hub": acc_hub,
            "project": acc_project,
            "folder": acc_folder,
            "file": acc_file
        }
        
        update_project_meta(
            project_id,  
            client, status, nit, legal_name, po_number,
            amount, emoji, start_date, duration_months,
            additional_time_months, paid_amount, square_meters, category=category,
            archived=project.archived,
            acc_config=acc_config
        )
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.post("/project/{project_id}/delete")
async def delete_project(project_id: str):
    # root_path = get_root_path() # Removed
    project = get_project_details(project_id)
    if project:
        update_project_meta(
            project_id,  
            project.client, project.status, project.nit, project.legal_name, project.po_number,
            project.amount, project.emoji, project.start_date, project.duration_months,
            project.additional_time_months, project.paid_amount, project.square_meters, category=project.category,
            archived=True # Set Archived to True
        )
    return RedirectResponse("/", status_code=303)

@app.post("/project/{project_id}/restore")
async def restore_project(project_id: str):
    # root_path = get_root_path() # Removed
    project = get_project_details(project_id)
    if project:
        update_project_meta(
            project_id,  
            project.client, project.status, project.nit, project.legal_name, project.po_number,
            project.amount, project.emoji, project.start_date, project.duration_months,
            project.additional_time_months, project.paid_amount, project.square_meters, category=project.category,
            archived=False # Set Archived to False
        )
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.post("/project/{project_id}/reminder/add")
async def add_reminder(project_id: str, title: str = Form(...), date: str = Form(...), frequency: str = Form("Once")):
    # root_path = get_root_path() # Removed
    add_project_reminder(project_id, title, date, frequency)
    return RedirectResponse(f"/project/{project_id}", status_code=303)

# Calendar specific routes
@app.post("/calendar/reminder/add")
async def add_calendar_reminder(
    project_id: str = Form(...),
    title: str = Form(...),
    date: str = Form(...),
    frequency: str = Form("Once")
):
    # root_path = get_root_path() # Removed
    if add_project_reminder(project_id, title, date, frequency):
        return RedirectResponse("/calendar", status_code=303)
    return RedirectResponse("/calendar?error=failed", status_code=303) 

@app.post("/project/{project_id}/reminder/delete")
async def delete_reminder(project_id: str, reminder_id: str = Form(...), redirect_to: str = Form(None)):
    # root_path = get_root_path() # Removed
    delete_project_reminder(project_id, reminder_id)
    
    if redirect_to and redirect_to == "calendar":
         return RedirectResponse("/calendar", status_code=303)
         
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.post("/project/{project_id}/reminder/toggle")
async def toggle_reminder(project_id: str, reminder_id: str = Form(...)):
    # root_path = get_root_path() # Removed
    toggle_project_reminder(project_id, reminder_id)
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.post("/project/{project_id}/collaborators/update")
async def update_project_collabs(project_id: str, request: Request):
    # root_path = get_root_path() # Removed
    data = await request.json() 
    # data should be { collab_id: percentage, ... }
    
    # Simple validation/sanitization
    assignments = {}
    for cid, pct in data.items():
        try:
            assignments[str(cid)] = float(pct)
        except: pass
        
    update_project_collaborators(project_id, assignments)
    return JSONResponse({"status": "ok"})


@app.post("/project/{project_id}/profit/update")
async def update_profit_config(
    project_id: str,
    projected_margin: str = Form("0.0"),
    real_margin: str = Form("0.0"),
    # We will receive partner shares as dynamic form fields, let's just grab form body directly if possible or known keys.
    # FastAPI Form doesn't support dynamic dict easily. We can assume key pattern "partner_share_{id}"
    request: Request = None
):
    # root_path = get_root_path() # Removed
    
    # Parse form data manually for dynamic keys
    form = await request.form()
    partners_config = {}
    
    for key, value in form.items():
        if key.startswith("partner_share_"):
            collab_id = key.replace("partner_share_", "")
            try:
                partners_config[collab_id] = float(value)
            except:
                pass
                
    try:
        p_margin = float(projected_margin)
    except: p_margin = 0.0
    
    try:
        r_margin = float(real_margin)
    except: r_margin = 0.0
    
    update_project_profit_config(project_id, p_margin, r_margin, partners_config)
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.post("/project/{project_id}/withdrawal/add")
async def add_withdrawal(project_id: str, collab_id: str = Form(...), amount: str = Form(...), note: str = Form("")):
    # root_path = get_root_path() # Removed
    try:
        amt = float(amount)
        add_partner_withdrawal(project_id, collab_id, amt, note)
    except:
        pass
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.get("/project_file/{project_id}/{category}/{filename}")
async def serve_project_file(project_id: str, category: str, filename: str):
    # root_path = get_root_path() # Removed
    project = get_project_details(project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
        
    # Security check: Ensure we are inside project path
    target_dir = os.path.join(os.path.abspath("Projects"), project.id, category)
    file_path = os.path.join(target_dir, filename)
    
    if not os.path.exists(file_path):
        return HTMLResponse("File not found", status_code=404)
        
    return FileResponse(file_path)

@app.post("/project/{project_id}/upload")
async def upload_file(project_id: str, category: str = Form(...), amount: str = Form(None), note: str = Form(""), file_date: str = Form(None), file: UploadFile = File(...)):
    # root_path = get_root_path() # Removed
    project = get_project_details(project_id)
    if project:
        target_dir = os.path.join(os.path.abspath("Projects"), project.id, category)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        file_path = os.path.join(target_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # If amount provided or note provided, save metadata
        # Even if amount is 0, if there is a note we might want to save it?
        # But previous logic only checked if amount. Let's keep checking valid amount for now, 
        # or just save if either exists.
        # Actually checking 'if amount' handles 'None' or empty string.
        # But if amount is missing but note exists, we still want to save the note.
        
        # Always save metadata to ensure file appears in the list
        val = 0.0
        if amount and amount.strip():
             try:
                 val = float(amount)
             except: pass
             
        try:
             # Note default text "Initial upload" is good only if note is empty
             final_note = note if note and note.strip() else "" 
             update_project_file_meta(project_id, category, file.filename, val, final_note, file_date)
        except Exception as e:
             print(f"ERROR: Failed to save metadata during upload: {e}")
             pass
            
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.post("/project/{project_id}/file/update_meta")
async def update_file_metadata(project_id: str, category: str = Form(...), filename: str = Form(...), amount: str = Form(None), note: str = Form("")):
    try:
        val = 0.0
        if amount and amount.strip():
            try: val = float(amount)
            except: pass
            
        update_project_file_meta(project_id, category, filename, val, note)
    except Exception as e:
        print(f"ERROR: Failed to update metadata: {e}")
        pass
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.post("/project/{project_id}/file/delete")
async def delete_file(project_id: str, category: str = Form(...), filename: str = Form(...)):
    project = get_project_details(project_id)
    if project:
        file_path = os.path.join(os.path.abspath("Projects"), project.id, category, filename)
        if os.path.exists(file_path):
             os.remove(file_path)
             # Remove from meta
             from database import delete_project_file_meta
             delete_project_file_meta(project_id, category, filename)
             
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.post("/project/{project_id}/file/move")
async def move_file(project_id: str, filename: str = Form(...), current_category: str = Form(...), new_category: str = Form(...)):
    # root_path = get_root_path() # Removed
    project = get_project_details(project_id)
    if project:
        src_path = os.path.join(os.path.abspath("Projects"), project.id, current_category, filename)
        dest_dir = os.path.join(os.path.abspath("Projects"), project.id, new_category)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        dest_path = os.path.join(dest_dir, filename)
        
        if os.path.exists(src_path):
            shutil.move(src_path, dest_path)
            # TODO: Move metadata too? Currently simply moving file.
            pass
            
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@app.post("/project/{project_id}/file/update_date")
async def update_file_date(project_id: str, category: str = Form(...), filename: str = Form(...), new_date: str = Form(...)):
    # root_path = get_root_path() # Removed
    project = get_project_details(project_id)
    if project:
        file_path = os.path.join(os.path.abspath("Projects"), project.id, category, filename)
        if os.path.exists(file_path) and new_date:
            try:
                # Parse YYYY-MM-DD
                dt = datetime.datetime.strptime(new_date, "%Y-%m-%d")
                # Set time to noon to avoid timezone edge cases
                dt = dt.replace(hour=12)
                timestamp = dt.timestamp()
                os.utime(file_path, (timestamp, timestamp))
            except Exception as e:
                print(f"Error updating date: {e}")
                
    return RedirectResponse(f"/project/{project_id}", status_code=303)



# ==========================================
# MARKET STUDY ROUTES
# ==========================================

@app.post("/cotizador/market/add")
async def add_market_study_route(
    name: str = Form(...),
    amount: float = Form(...),
    square_meters: float = Form(...),
    months: float = Form(...),
    category: str = Form(...)
):
    # root_path = get_root_path() # Removed
    add_market_study(name, amount, square_meters, months, category)
    return RedirectResponse("/cotizador", status_code=303)

@app.post("/cotizador/market/delete")
async def delete_market_study_route(study_id: str = Form(...)):
    # root_path = get_root_path() # Removed
    delete_market_study(study_id)
    return RedirectResponse("/cotizador", status_code=303)


# ==========================================
# ESTIMACIONES ROUTES
# ==========================================



@app.post("/estimaciones/create")
async def create_estimation_route(
    name: str = Form(...),
    amount: float = Form(0.0),
    square_meters: float = Form(0.0),
    client: str = Form(""),
    category: str = Form("Residencial"),
    start_date: str = Form(""),
    duration_months: float = Form(0.0),
    nit: str = Form(""),
    legal_name: str = Form(""),
    po_number: str = Form(""),
):
    # root_path = get_root_path() # Removed
    data = {
        "name": name,
        "amount": amount,
        "square_meters": square_meters,
        "client": client,
        "category": category,
        "start_date": start_date,
        "duration_months": duration_months,
        "nit": nit,
        "legal_name": legal_name,
        "po_number": po_number,
        "status": "Analisis"
    }
    
    create_estimation(data)
    return RedirectResponse("/estimaciones", status_code=303)

@app.post("/estimaciones/update/status")
async def update_estimation_status(
    est_id: str = Form(...),
    new_status: str = Form(...)
):
    # root_path = get_root_path() # Removed
    update_estimation(est_id, {"status": new_status})
    return JSONResponse({"status": "success"})

@app.post("/estimaciones/delete")
async def delete_estimation_route(est_id: str = Form(...)):
    # root_path = get_root_path() # Removed
    delete_estimation(est_id)
    return RedirectResponse("/estimaciones", status_code=303)



@app.get("/estimaciones/{est_id}")
async def get_estimation_details_route(est_id: str):
    # root_path = get_root_path() # Removed
    from database import get_estimation_details
    data = get_estimation_details(est_id)
    if not data: return JSONResponse({"error": "Not Found"}, status_code=404)
    return JSONResponse(data)

@app.post("/estimaciones/update/full")
async def update_estimation_full_route(request: Request):
    # root_path = get_root_path() # Removed
    data = await request.json()
    from database import update_estimation_full
    success = update_estimation_full(data)
    if success:
        return JSONResponse({"status": "success"})
    else:
        return JSONResponse({"status": "error"}, status_code=500)

@app.get("/hr", response_class=HTMLResponse)
async def read_hr(request: Request, view: str = "active"):
    # root_path = get_root_path() # Removed
    collaborators = get_collaborators()
    
    # Calculate Dashboard Metrics (Filter by Active and NOT Archived)
    # Metrics always reflect the "Operational" state, so we excludes archived and inactive.
    # User said: "part of accounting process because expenses were made".
    # But usually dashboard is "Current". Let's stick to Active & Unarchived for main stats.
    # Total Liabilty might need to include everyone?
    # Let's keep metrics for "Active Workforce".
    
    active_operating_collabs = [c for c in collaborators if getattr(c, 'status', 'Activo') == 'Activo' and not getattr(c, 'archived', False)]
    
    total_collabs = len(active_operating_collabs)
    monthly_payroll = sum(c.salary for c in active_operating_collabs)
    annual_payroll = monthly_payroll * 12 
    total_liability = sum(c.accumulated_liability for c in active_operating_collabs)
    total_employer_costs = sum((c.base_salary * (0.1067 + 0.01 + 0.01)) for c in active_operating_collabs)
    
    # Birthday Calendar (Active only)
    current_month = datetime.datetime.now().month
    birthdays = []
    for c in active_operating_collabs:
        if c.birthday:
            try:
                b_date = datetime.datetime.strptime(c.birthday, "%Y-%m-%d")
                if b_date.month == current_month:
                    birthdays.append({
                        "name": c.name,
                        "day": b_date.day,
                        "date": b_date.strftime("%d/%m")
                    })
            except:
                pass
    birthdays.sort(key=lambda x: x['day'])
    
    # Filter by view mode (Archived vs Active)
    # Default: Show only non-archived
    # If view="archived", show ONLY archived
    filtered_collabs = []
    if view == 'archived':
        filtered_collabs = [c for c in collaborators if getattr(c, 'archived', False)]
    else:
        filtered_collabs = [c for c in collaborators if not getattr(c, 'archived', False)]
        
    # Group by Role
    role_order = ["Bim Manager", "Bim Coordinator", "Bim Modeler", "Bim Drafter", "Administrativo", "Socio"]
    grouped_collabs = {role: [] for role in role_order}
    grouped_collabs["Otros"] = []
    
    for c in filtered_collabs:
        found = False
        for r in role_order:
            if r.lower() in c.role.lower() or c.role.lower() in r.lower():
                 grouped_collabs[r].append(c)
                 found = True
                 break
        if not found:
             grouped_collabs["Otros"].append(c)
             
    if not grouped_collabs["Otros"]:
        del grouped_collabs["Otros"]

    return templates.TemplateResponse("hr.html", {
        "request": request,
        "grouped_collabs": grouped_collabs,
        "metrics": {
            "total_collabs": total_collabs,
            "monthly_payroll": monthly_payroll,
            "annual_payroll": annual_payroll,
            "total_liability": total_liability,
            "total_employer_costs": total_employer_costs
        },
        "birthdays": birthdays,
        "current_month_name": datetime.datetime.now().strftime("%B"),
        "view_mode": view
    })

@app.post("/hr/create")
async def create_hr(name: str = Form(...), role: str = Form("Collaborator"), salary: str = Form("0"), birthday: str = Form(""), start_date: str = Form("")):
    # root_path = get_root_path() # Removed
    print(f"DEBUG: create_hr called with: name={name}, role={role}, salary={salary}, birthday={birthday}, start_date={start_date}")
    
    # Safe conversion for salary
    try:
        salary_float = float(salary) if salary and salary.strip() else 0.0
    except ValueError:
        print(f"DEBUG: Salary conversion failed for '{salary}', using 0.0")
        salary_float = 0.0
        
    try:
        result = create_collaborator(name, role, salary_float, birthday, start_date)
        print(f"DEBUG: create_collaborator result: {result}")
    except Exception as e:
        print(f"DEBUG: Exception calling create_collaborator: {e}")
        
    return RedirectResponse("/hr", status_code=303)

@app.post("/hr/{collab_id}/update")
async def update_hr_details(collab_id: str, 
                            role: str = Form("Collaborator"), 
                            base_salary: str = Form("0"), 
                            bonus_incentive: str = Form("250"), 
                            birthday: str = Form(""), 
                            start_date: str = Form(""),
                            status: str = Form("Activo"),
                            email: str = Form("")):
    # root_path = get_root_path() # Removed
    
    # Safe conversions
    try:
        base_salary_float = float(base_salary) if base_salary and base_salary.strip() else 0.0
    except ValueError:
        base_salary_float = 0.0
        
    try:
        bonus_incentive_float = float(bonus_incentive) if bonus_incentive and bonus_incentive.strip() else 0.0
    except ValueError:
        bonus_incentive_float = 0.0

    print(f"DEBUG: update_hr_details called for {collab_id}")
    print(f"DEBUG: Received fields: role={role}, base={base_salary}, bonus={bonus_incentive}, bday={birthday}, start={start_date}, status={status}, email={email}")

    try:
        success = update_collaborator(
            collab_id, 
            role=role, 
            base_salary=base_salary_float, 
            bonus_incentive=bonus_incentive_float, 
            birthday=birthday, 
            start_date=start_date, 
            status=status, 
            email=email
        )
        print(f"DEBUG: update_collaborator returned: {success}")
    except Exception as e:
        print(f"CRITICAL ERROR in update_hr_details: {e}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"Internal Server Error: {e}", status_code=500)
        
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@app.post("/hr/{collab_id}/upload_picture")
async def upload_hr_picture(collab_id: str, file: UploadFile = File(...)):
    # root_path = get_root_path() # Removed
    collab = get_collaborator_details(collab_id)
    
    if collab and file.filename:
        safe_filename = file.filename
        # Save to Profile folder
        target_path = os.path.join(os.path.abspath("Collaborators"), collab.id, "Profile", safe_filename)
        profile_dir = os.path.dirname(target_path)
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir)
            
        try:
            with open(target_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
                
            # Update meta reference
            update_collaborator_picture(collab_id, safe_filename)
        except Exception as e:
            print(f"Error saving profile picture: {e}")
            
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)


@app.get("/hr/{collab_id}/plugin_logs", response_class=HTMLResponse)
async def read_hr_plugin_logs(request: Request, collab_id: str, start_date: str = None, end_date: str = None):
    # root_path = get_root_path() # Removed
    collab = get_collaborator_details(collab_id)
    if not collab: return RedirectResponse("/hr")
    
    from database import get_user_plugin_stats, get_plugin_sessions
    
    # 1. Stats
    stats = get_user_plugin_stats(collab.email)
    
    # 2. Detailed Logs from DB helper
    from database import get_user_plugin_logs
    
    # Parse Dates
    dt_start = None
    dt_end = None
    if start_date:
        try: dt_start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        except: pass
    if end_date:
        try: dt_end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except: pass
        
    session_logs = get_user_plugin_logs(collab.email, start_date=dt_start, end_date=dt_end)
        
    return templates.TemplateResponse("plugin_user_logs.html", {
        "request": request, 
        "c": collab,
        "stats": stats,
        "session_logs": session_logs,
        "current_month": datetime.datetime.now().strftime("%B")
    })

@app.get("/hr/{collab_id}", response_class=HTMLResponse)
async def read_hr_detail(request: Request, collab_id: str):
    try:
        # root_path = get_root_path() # Removed
        collab = get_collaborator_details(collab_id)
        if not collab:
            return RedirectResponse("/hr")
            
        # 1. ISR Calculation
        isr_projection = calculate_isr_projection(collab.base_salary, collab.bonus_incentive)
        
        # 2. Adjustments Totals
        # Safely handle adjustments if None (though DB defaults to [])
        adjs = collab.adjustments if hasattr(collab, 'adjustments') and collab.adjustments else []
        total_bonos = sum(float(a['amount']) for a in adjs if a['type'] == 'Bono')
        total_descuentos = sum(float(a['amount']) for a in adjs if a['type'] == 'Descuento')
        
        # 3. Monthly Calculations
        igss_laboral = collab.base_salary * 0.0483
        # Net Pay = (Base + Bonus + Bonos) - (IGSS + ISR + Descuentos)
        liquid_to_receive = (collab.base_salary + collab.bonus_incentive + total_bonos) - (igss_laboral + isr_projection + total_descuentos)
        
        # 4. Historical Totals (Approximation)
        months_worked = get_months_worked(collab.start_date)
        hist_total_earned = months_worked * (collab.base_salary + collab.bonus_incentive) # Approx
        hist_employer_costs = months_worked * (collab.base_salary * (0.1067 + 0.01 + 0.01)) # IGSS+Intecap+Irtra
        hist_liability = months_worked * (collab.base_salary * (0.0833 + 0.0833 + 0.0417)) # Aguinaldo+Bono14+Vacas
        
        # Pass plain dicts or calculated values
        calc_data = {
            "isr_projection": isr_projection,
            "total_bonos": total_bonos,
            "total_descuentos": total_descuentos,
            "igss_laboral": igss_laboral,
            "liquid_to_receive": liquid_to_receive,
            "hist_total_earned": hist_total_earned,
            "hist_employer_costs": hist_employer_costs,

            "hist_liability": hist_liability,
            "months_worked": months_worked,
            "current_month_name": datetime.datetime.now().strftime("%B"),
        }
        
        # --- PLUGIN STATS INTEGRATION ---
        # Match by email
        from database import get_user_plugin_stats
        plugin_stats = get_user_plugin_stats(collab.email)
        calc_data["plugin_stats"] = plugin_stats
        # --------------------------------
        
        # Add additional month/year data to calc_data
        calc_data.update({
            "current_month_year": datetime.datetime.now().strftime("%Y-%m"),
            "next_month_name": (datetime.datetime.now() + datetime.timedelta(days=32)).strftime("%B"),
            "next_month_year": (datetime.datetime.now() + datetime.timedelta(days=32)).strftime("%Y-%m")
        })
        
        assigned_projects = get_collaborator_assigned_projects(collab_id)
    
        return templates.TemplateResponse("hr_detail.html", {
            "request": request, 
            "c": collab,
            "calc": calc_data,
            "assigned_projects": assigned_projects
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<h1>Internal Server Error</h1><pre>{traceback.format_exc()}</pre>", status_code=500)

@app.post("/hr/{collab_id}/adjustment/add")
async def create_adjustment(collab_id: str, type: str = Form(...), description: str = Form(...), amount: str = Form(...)):
    # root_path = get_root_path() # Removed
    try:
        amt = float(amount)
        add_adjustment(collab_id, type, description, amt)
    except:
        pass
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@app.post("/hr/{collab_id}/adjustment/remove")
async def delete_adjustment(collab_id: str, adj_id: str = Form(...)):
    # root_path = get_root_path() # Removed
    remove_adjustment(collab_id, adj_id)
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@app.post("/hr/{collab_id}/archive")
async def archive_collaborator_route(collab_id: str, archive: bool = Form(...)):
    # root_path = get_root_path() # Removed
    toggle_archive_collaborator(collab_id, archive)
    return RedirectResponse("/hr", status_code=303)

@app.post("/hr/{collab_id}/payroll/close")
async def close_payroll_month(collab_id: str, month_year: str = Form(None)):
    try:
        # root_path = get_root_path() # Removed
        collab = get_collaborator_details(collab_id)
        if not collab:
            return RedirectResponse(f"/hr", status_code=303)
        
        # 1. Calculate Monthly Totals
        # Safely handle adjustments
        adjs = collab.adjustments if hasattr(collab, 'adjustments') and collab.adjustments else []
        total_bonos = sum(float(a['amount']) for a in adjs if a['type'] == 'Bono')
        total_descuentos = sum(float(a['amount']) for a in adjs if a['type'] == 'Descuento')
        
        isr_proj = calculate_isr_projection(collab.base_salary, collab.bonus_incentive)
        igss_laboral = collab.base_salary * 0.0483
        
        liquid = (collab.base_salary + collab.bonus_incentive + total_bonos) - (igss_laboral + isr_proj + total_descuentos)
        
        # Manufacturer/Provider Costs
        igss_patro = collab.base_salary * 0.1067
        intecap = collab.base_salary * 0.01
        irtra = collab.base_salary * 0.01
        
        # Liabilities
        aguinaldo = collab.base_salary / 12
        bono14 = collab.base_salary / 12
        vacas = collab.base_salary / 24
        total_liability_month = aguinaldo + bono14 + vacas

        # 2. Update Accumulated Liability in DB
        # We need to save this back to meta.json
        new_liability = getattr(collab, 'accumulated_liability', 0.0) + total_liability_month
        
        # 3. Create Record for Excel
        import pandas as pd
        
        # Use selected month/year or default to now
        if month_year:
            # Parse month_year "YYYY-MM"
            try:
                record_date = datetime.datetime.strptime(month_year + "-01", "%Y-%m-%d") # defaults to 1st of month
                record_month_str = record_date.strftime("%B")
                record_date_str = record_date.strftime("%Y-%m-%d") # Or end of month? Let's use 1st for record keeping or now? User didn't specify date, just month.
                # Use end of month for "Date" field? Or just the date of closing?
                # Usually Ledger has "Date of Payment". Let's assume closing = payment date.
                # But if I select "October" and I close in "November", maybe I want the date to be Oct 30?
                # Let's keep it simple: "Mes" field reflects the selected month. "Fecha" reflects actual close date (Audit trail).
                selected_month_name = record_month_str
            except:
                 selected_month_name = datetime.datetime.now().strftime("%B")
        else:
             selected_month_name = datetime.datetime.now().strftime("%B")
        
        record = {
            "Fecha Pago": datetime.datetime.now().strftime("%Y-%m-%d"),
            "Mes Correspondiente": selected_month_name,
            "Salario Base": collab.base_salary,
            "Bonificación": collab.bonus_incentive,
            "Otros Bonos": total_bonos,
            "Descuentos": total_descuentos,
            "IGSS Laboral": igss_laboral,
            "ISR": isr_proj,
            "Líquido Recibido": liquid,
            "IGSS Patronal": igss_patro,
            "INTECAP": intecap,
            "IRTRA": irtra,
            "Prov. Aguinaldo": aguinaldo,
            "Prov. Bono14": bono14,
            "Prov. Vacaciones": vacas,
            "Pasivo Mensual": total_liability_month
        }
        
        # 4. Save to Excel
        payment_dir = os.path.join(os.path.abspath("Collaborators"), collab.id, "Payments")
        if not os.path.exists(payment_dir):
            os.makedirs(payment_dir)
            
        excel_path = os.path.join(payment_dir, "Libro_Salarios.xlsx")
        
        if os.path.exists(excel_path):
            df = pd.read_excel(excel_path)
            new_df = pd.DataFrame([record])
            df = pd.concat([df, new_df], ignore_index=True)
        else:
            df = pd.DataFrame([record])
            
        df.to_excel(excel_path, index=False)
        
        # 5. Clear Adjustments & Save Meta
        # We reuse update_collaborator but we need to pass strict params.
        # It's cleaner to implement a specific 'close_month_update' in database or use update_collaborator carefully.
        # But update_collaborator doesn't support setting adjustments or accumulated_liability directly yet in the signature?
        # Let's check update_collaborator signature. It takes specific args.
        # We should update database.py to allow saving adjustments/liability.
        # FOR NOW: We will read/write meta.json directly here for speed, or add a function in database.py.
        # Direct write is risky if concurrency, but safe for single user.
        # Let's do it via a new database function call to be clean.
        from database import save_payroll_close
        save_payroll_close(collab_id, new_liability)

    except Exception as e:
        print(f"Error closing payroll: {e}")
        import traceback
        traceback.print_exc()
        
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@app.get("/hr/{collab_id}/plugin_logs")
async def view_plugin_logs(collab_id: str, request: Request):
    try:
        # root_path = get_root_path() # Removed
        collab = get_collaborator_details(collab_id)
        if not collab:
            return RedirectResponse("/hr", status_code=303)
            
        from database import get_user_plugin_logs, get_user_plugin_stats
        
        # Ensure email is present
        email = collab.email if collab.email else ""
        
        logs = get_user_plugin_logs(email)
        stats = get_user_plugin_stats(email)
        
        return templates.TemplateResponse("plugin_user_logs.html", {
            "request": request, 
            "c": collab,
            "session_logs": logs,
            "stats": stats,
            "current_month": datetime.datetime.now().strftime("%B")
        })
    except Exception as e:
        print(f"Error viewing logs: {e}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"Error: {e}", status_code=500)

@app.get("/project/{project_id}/file/{category}/{filename}")
async def get_file_content(project_id: str, category: str, filename: str):
    # root_path = get_root_path() # Removed
    project = get_project_details(project_id)
    if not project:
        return RedirectResponse("/")
        
    file_path = os.path.join(os.path.abspath("Projects"), project.id, category, filename)
    if not os.path.exists(file_path):
        return HTMLResponse("File not found", status_code=404)
        
    return FileResponse(file_path)

@app.get("/project/{project_id}/view/{category}/{filename}", response_class=HTMLResponse)
async def view_file_page(request: Request, project_id: str, category: str, filename: str):
    # root_path = get_root_path() # Removed
    project = get_project_details(project_id)
    if not project:
         return RedirectResponse("/")

    # Determine type for viewer
    ext = os.path.splitext(filename)[1].lower()
    file_type = "other"
    if ext == ".pdf":
        file_type = "pdf"
    elif ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
        file_type = "image"
    elif ext in [".xlsx", ".xls", ".csv"]:
        file_type = "spreadsheet"
    elif ext in [".docx", ".doc", ".txt"]:
        file_type = "document"
        
    file_url = f"/project/{project_id}/file/{category}/{filename}"
    
    return templates.TemplateResponse("file_viewer.html", {
        "request": request,
        "p": project,
        "filename": filename,
        "category": category,
        "file_url": file_url,
        "file_type": file_type
    })

@app.post("/hr/{collab_id}/upload")
async def upload_hr_file(collab_id: str, category: str = Form(...), file: UploadFile = File(...)):
    # root_path = get_root_path() # Removed
    collab = get_collaborator_details(collab_id)
    if collab:
        target_dir = os.path.join(os.path.abspath("Collaborators"), collab.id, category)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        file_path = os.path.join(target_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@app.get("/timeline", response_class=HTMLResponse)
async def read_timeline(request: Request):
     # Just redirect to home for timeline view now
    return RedirectResponse("/")

@app.get("/cotizador")
async def cotizador_view(request: Request):
    # root_path = get_root_path() # Removed
    projects = get_projects()
    # Get collaborators for "Socios" dropdown
    collabs = get_collaborators()
    
    # Filter only active or all? User said "resumen de todos los proyectos"
    # We pass all.
    return templates.TemplateResponse("cotizador.html", {
        "request": request, 
        "projects": projects,
        "collaborators": collabs
    })

@app.get("/hr_file/{collab_id}/{category}/{filename}")
async def get_hr_file(collab_id: str, category: str, filename: str):
    # root_path = get_root_path() # Removed
    collab = get_collaborator_details(collab_id)
    if not collab:
        return HTMLResponse("Not Found", status_code=404)
        
    file_path = os.path.join(os.path.abspath("Collaborators"), collab.id, category, filename)
    if not os.path.exists(file_path):
        return HTMLResponse("File not found", status_code=404)
        
    return FileResponse(file_path)


# ========================
# Gastos (Expenses) Routes
# ========================



@app.get("/socios", response_class=HTMLResponse)
async def read_socios(request: Request):
    projects = get_projects()
    # Get only socio collaborators (or everyone? usually partners only)
    # Let's filter by role "Socio".
    collaborators = get_collaborators()
    partners = [c for c in collaborators if "socio" in c.role.lower()]
    
    # Calculate Partner Stats
    # We need a structure:
    # { partner_id: { collab: CollabObj, projects: [ {project: ProjObj, share_pct, total_profit, withdrawn, balance } ], total_balance: float } }
    
    partner_stats = {}
    
    for p in partners:
        partner_stats[p.id] = {
            "collab": p,
            "project_details": [],
            "total_balance": 0.0,
            "total_withdrawn": 0.0,
            "total_profit": 0.0
        }
        
    for proj in projects:
        # Check if project has config
        shares = getattr(proj, 'partners_config', {}) or {}
        
        # Calculate Project Utility Pool
        # Formula: Paid Amount * Real Margin? Or Total Amount * Real Margin?
        # Usually it's based on Revenue. Let's use Real Margin on Paid Amount (Cash flow basis) or Total Amount (Accrual)?
        # User said "percentage of real utility perceived".
        # Let's assume: Pool = proj.amount * (proj.real_profit_margin / 100)
        # OR Pool = proj.paid_amount * ...?
        # Let's use Total Amount for "Projected" and manual tracking?
        # Let's use: Real Profit Pool = proj.amount * (real_margin / 100).
        
        profit_pool = (proj.amount or 0.0) * ((proj.real_profit_margin or 0.0) / 100.0)
        
        for p_id in partner_stats.keys():
            share_pct = shares.get(p_id, 0.0)
            
            if share_pct > 0:
                partner_share_amount = profit_pool * (share_pct / 100.0)
                
                # Calculate Withdrawals for this partner in this project
                withdrawn = 0.0
                if proj.profit_withdrawals:
                     withdrawn = sum(w['amount'] for w in proj.profit_withdrawals if w['collab_id'] == p_id)
                
                balance = partner_share_amount - withdrawn
                
                partner_stats[p_id]["project_details"].append({
                    "project_name": proj.name,
                    "project_id": proj.id,
                    "share_pct": share_pct,
                    "total_profit_share": partner_share_amount,
                    "withdrawn": withdrawn,
                    "balance": balance,
                    "project_emoji": proj.emoji
                })
                
                partner_stats[p_id]["total_profit"] += partner_share_amount
                partner_stats[p_id]["total_withdrawn"] += withdrawn
                partner_stats[p_id]["total_balance"] += balance

    return templates.TemplateResponse("socios.html", {
        "request": request,
        "partners": partner_stats
    })

@app.post("/create_project")
async def create_project_route(
    name: str = Form(...), 
    client: str = Form(""), 
    nit: str = Form(""),
    legal_name: str = Form(""),
    po_number: str = Form(""),
    amount: float = Form(0.0),
    status: str = Form("Activo"),
    emoji: str = Form("📁"),
    custom_id: str = Form(None)
):
    print(f"DEBUG: Endpoint /create_project hit. Name={name}")
    success = create_project(name, client, nit, legal_name, po_number, amount, status, emoji, custom_id)
    if success:
         print("Create Project: Success")
    else:
         print("Create Project: Failed internal logic")
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/projects/stats")
async def get_stats():
    try:
        data = get_project_stats_by_category()
        return JSONResponse(data)
    except Exception as e:
        print(f"Error stats: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/gastos", response_class=HTMLResponse)
async def read_gastos(request: Request, year: str = ""):
    # root_path = get_root_path() # Removed
    
    # Determine Year
    current_year = datetime.datetime.now().year
    try:
        selected_year = int(year)
    except:
        selected_year = current_year
        
    expenses = get_expenses_monthly(selected_year)
    
    # Calculate Subtotals
    # expenses is now a LIST of DICTS (Months)
    for col in expenses:
        # col['cards'] are dicts now, so this works:
        total = sum(c['amount'] for c in col['cards'])
        col['total'] = total
        
    # Calculate Grand Total
    grand_total = sum(col['total'] for col in expenses)
    
    # Available years (simple range for now, or scan DB)
    # Let's offer just Current-1, Current, Current+1 for now
    available_years = [current_year - 1, current_year, current_year + 1]

    return templates.TemplateResponse("gastos.html", {
        "request": request,
        "expenses": expenses,
        "selected_year": selected_year,
        "available_years": available_years,
        "grand_total": grand_total
    })

@app.post("/gastos/column/add")
async def add_gastos_column(name: str = Form(...)):
    # root_path = get_root_path() # Removed
    # Legacy: Still useful if they really want to add a column? 
    # But now expenses is Monthly View. Column Add is likely useless unless backend supports multiple views.
    # Keep it to avoid 404 if called.
    add_expense_column(name)
    return RedirectResponse("/gastos", status_code=303)

@app.post("/gastos/card/add")
async def add_gastos_card(
    column_id: str = Form(...),
    name: str = Form(...),
    amount: float = Form(...),
    description: str = Form(""),
    date: str = Form(None), # Added Date
    files: List[UploadFile] = File(None)
):
    from typing import List
    # root_path = get_root_path() # Removed
    
    # Create card
    # Pass date. If date is None, database.py sets it to today.
    # column_id might be "month-index" or a dummy.
    # database.py handles dummy column id logic.
    card = add_expense_card(column_id, name, amount, description, [], date)
    
    if card and files:
        saved_filenames = []
        # Save to Expenses/{card_id}
        expense_dir = os.path.join(os.path.abspath("Expenses"), card['id'])
        if not os.path.exists(expense_dir):
            os.makedirs(expense_dir)
            
        for file in files:
            if file.filename:
                file_path = os.path.join(expense_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                saved_filenames.append(file.filename)
        
        if saved_filenames:
            # update_expense_card_files(root_path, card['id'], saved_filenames) # Need to clean this func or it will fail?
            # update_expense_card_files arg removed in database.py
            update_expense_card_files(card['id'], saved_filenames)
            
    return RedirectResponse("/gastos", status_code=303)

@app.post("/gastos/card/copy")
async def copy_gastos_card(
    card_id: str = Form(...),
    target_column_id: str = Form(...)
):
    # root_path = get_root_path() # Removed
    new_card_id = copy_expense_card(card_id, target_column_id)
    
    if new_card_id:
        src_dir = os.path.join(os.path.abspath("Expenses"), card_id)
        if os.path.exists(src_dir):
             dest_dir = os.path.join(os.path.abspath("Expenses"), new_card_id)
             # copytree requires dest to NOT exist usually, or use dirs_exist_ok in 3.8+
             # Since ID is new, it shouldn't exist.
             try:
                shutil.copytree(src_dir, dest_dir)
             except: pass
                 
    return RedirectResponse("/gastos", status_code=303)

@app.get("/gastos/file/{card_id}/{filename}")
async def get_gastos_file(card_id: str, filename: str):
    file_path = os.path.join(os.path.abspath("Expenses"), card_id, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTMLResponse("File not found", status_code=404)

@app.post("/gastos/card/delete")
async def delete_gastos_card(card_id: str = Form(...)):
    # root_path = get_root_path() # Removed
    delete_expense_card(card_id)
    return RedirectResponse("/gastos", status_code=303)

@app.post("/gastos/column/delete")
async def delete_gastos_column(column_id: str = Form(...)):
    # root_path = get_root_path() # Removed
    delete_expense_column(column_id)
    return RedirectResponse("/gastos", status_code=303)

# -----------------------------------------------------------------------------
# HR PAYMENTS (HISTORICAL)
# -----------------------------------------------------------------------------
@app.get("/hr/{collab_id}/payments", response_class=HTMLResponse)
async def view_payments(request: Request, collab_id: str):
    # root_path = get_root_path() # Removed
    c = get_collaborator_details(root_path, collab_id)
    if not c: return RedirectResponse("/hr")

    columns = []
    total_earned_history = 0.0
    
    try:
        start_date = datetime.datetime.strptime(c.start_date, "%Y-%m-%d")
    except:
        start_date = datetime.datetime.now()

    current_date = datetime.datetime.now()
    # Normalize to start of months
    curr = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    MONTHS_ES = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    # Safety loop limit
    loop_count = 0
    while curr <= end and loop_count < 1000:
        loop_count += 1
        month_key = curr.strftime("%Y-%m")
        month_name = f"{MONTHS_ES[curr.month]} {curr.year}"
        
        # Calculations (Assume constant salary for simplicity as per requirement)
        base = c.base_salary
        bonus = c.bonus_incentive
        igss = base * 0.0483
        
        # Monthly ISR
        isr_annual = calculate_isr_projection(base, bonus)
        isr_monthly = isr_annual / 12.0
        
        liquid = (base + bonus) - igss - isr_monthly
        
        # Find Adjustments for this Month
        col_adjustments = []
        adj_total = 0.0
        
        for adj in c.adjustments:
            try:
                # Parse ISO date 2023-12-01T...
                adj_date_str = adj.get("date", "")
                if adj_date_str:
                    adj_dt = datetime.datetime.fromisoformat(adj_date_str)
                    if adj_dt.year == curr.year and adj_dt.month == curr.month:
                        col_adjustments.append(adj)
                        if adj.get("type") == "Bono":
                            adj_total += float(adj.get("amount", 0))
                        else:
                            adj_total -= float(adj.get("amount", 0))
            except: pass
            
        final_total = liquid + adj_total
        total_earned_history += final_total
        
        columns.append({
            "name": month_name,
            "month_key": month_key,
            "is_current": (curr.year == current_date.year and curr.month == current_date.month),
            "base_data": {
                "salary": base + bonus,
                "igss": igss,
                "isr": isr_monthly,
                "liquid": liquid
            },
            "adjustments": col_adjustments,
            "total": final_total
        })
        
        # Increment Month
        if curr.month == 12:
            curr = curr.replace(year=curr.year + 1, month=1)
        else:
            curr = curr.replace(month=curr.month + 1)
            
    return templates.TemplateResponse("hr_payments.html", {
        "request": request, "c": c, "columns": columns, "total_earned": total_earned_history
    })

@app.post("/hr/{collab_id}/payments/add_adjustment")
async def add_adjustment_payment(
    collab_id: str, 
    type: str = Form(...), 
    description: str = Form(...), 
    amount: float = Form(...), 
    month_key: str = Form(...) # YYYY-MM
):
    # root_path = get_root_path() # Removed
    try:
        dt = datetime.datetime.strptime(month_key, "%Y-%m")
        # Store as 15th of the month to be safe within the month logic
        target_date = dt.replace(day=15).isoformat()
    except:
        target_date = datetime.datetime.now().isoformat()
        
    add_adjustment(collab_id, type, description, amount, date_str=target_date)
    return RedirectResponse(f"/hr/{collab_id}/payments", status_code=303)

@app.post("/hr/{collab_id}/adjustment/delete")
async def delete_adjustment_general(
    collab_id: str, 
    adj_id: str = Form(...), 
    redirect_to: str = Form(None)
):
    # root_path = get_root_path() # Removed
    remove_adjustment(collab_id, adj_id)
    
    # If specifically coming from payments view
    if redirect_to == "payments":
        return RedirectResponse(f"/hr/{collab_id}/payments", status_code=303)
        
    # Default fallback
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

# ==========================================
# CLIENT PORTAL & API ROUTES
# ==========================================

@app.post("/api/login")
async def api_login(credentials: LoginRequest):
    # root_path = get_root_path() # Removed
    user = get_user_by_email(credentials.username)
    
    if not user or not verify_password(credentials.password, user.hashed_password):
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
            "assigned_projects": user.assigned_projects,
            "permissions": user.permissions
        }
    }

@app.get("/api/projects", response_class=JSONResponse)
async def api_get_projects():
    # Admin only? Or limited data? For simplicity allowing getting names/IDs
    # root_path = get_root_path() # Removed
    all_projects = get_projects()
    
    # Return minimized list
    data = []
    for p in all_projects:
        data.append({
            "id": p.id,
            "name": p.name,
            "client": p.client,
            "status": p.status,
            "amount": p.amount,
            "paid": p.paid_amount,
            "emoji": p.emoji
        })
    return data

@app.get("/api/projects/stats", response_class=JSONResponse)
async def api_project_stats():
    from database import get_project_stats_by_category
    try:
        stats = get_project_stats_by_category()
        return stats
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/users", response_class=JSONResponse)
async def api_get_users():
    # root_path = get_root_path() # Removed
    # Ideally should check admin token here
    users = get_users()
    data = []
    for u in users:
        data.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "assigned_projects": u.assigned_projects,
            "permissions": u.permissions
        })
    return data

@app.post("/api/admin/users/assign")
async def api_assign_project(req: AssignProjectRequest, request: Request):
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "admin":
         raise HTTPException(status_code=403, detail="Not authorized")

    from database import update_user_permissions, update_user_assigned_projects

    # 1. Update Permissions
    update_user_permissions(req.user_id, req.permissions)
    
    # 2. Update Assigned Projects
    update_user_assigned_projects(req.user_id, req.project_ids)
    
    return {"status": "success"}

@app.get("/api/client/dashboard", response_class=JSONResponse)
async def api_client_dashboard(request: Request):
    # Retrieve user from token header manually since middleware handles cookies
    # For API fetch from JS, we use Authorization Header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Token")
        
    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid Token")
        
    email = payload.get("sub")
    user = get_user_by_email(email)
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    # Get Assigned Projects Data
    projects_data = []
    for pid in user.assigned_projects:
        p = get_project_details(pid)
        if p:
            # Respect permissions?
            # If financials=False, hide budget/paid
            show_fin = user.permissions.get("financials", False)
            
            p_data = {
                "id": p.id,
                "name": p.name,
                "location": p.legal_name, # Mapping Legal Name to Location for now or just generic
                "status": p.status,
                "projectedProgress": p.projected_profit_margin, # Using dummy field mapping or real logic
                "realProgress": p.real_profit_margin, # Using dummy mapping
                "image": "/hero.png", # Placeholder or find first image
                "start_date": p.start_date,
                "acc_config": getattr(p, 'acc_config', {})
            }
            
            if show_fin:
                p_data["budget"] = p.amount
                p_data["executed"] = p.paid_amount
            
            projects_data.append(p_data)
            
    return {
        "user": {
            "name": user.name,
            "email": user.email
        },
        "projects": projects_data
    }

@app.post("/cotizaciones/templates")
async def save_template_route(request: Request):
    try:
        data = await request.json()
        name = data.get("name")
        content = data.get("content_json")
        if not name or not content:
            return JSONResponse({"status": "error", "message": "Missing name or content"}, status_code=400)
            
        tpl_id = save_template(name, content)
        if tpl_id: return JSONResponse({"status": "success", "id": tpl_id})
        else: return JSONResponse({"status": "error", "message": "DB Error"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/cotizaciones/templates/{tpl_id}/delete")
async def delete_template_route(tpl_id: int):
    try:
        success = delete_template(tpl_id)
        if success: return JSONResponse({"status": "success"})
        else: return JSONResponse({"status": "error", "message": "Failed/Not Found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ==========================================
# ADMIN ROUTES (New)
# ==========================================


@app.get("/projects", response_class=HTMLResponse)
async def view_projects(request: Request):
    projects = get_projects()
    # Optional: Filter by user permissions if needed
    # For now, show all projects (Staff view)
    user = getattr(request.state, "user", None)
    
    # If client, filter only assigned?
    # Logic for client filtering could go here.
    # Assuming get_projects returns all.
    
    return templates.TemplateResponse("projects.html", {
        "request": request, 
        "projects": projects,
        "root_path": "Railway"
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = getattr(request.state, "user", None)
    _users = get_users()
    _projects = get_projects()
    error = request.query_params.get("error")
    success = request.query_params.get("success")

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "users": _users,
        "projects": _projects,
        "user": user,
        "error": error,
        "success": success
    })

@app.post("/admin/users/add")
async def admin_add_user(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("Member")
):
    try:
        hashed = get_password_hash(password)
        new_user = User(
            id=str(uuid.uuid4()),
            name=full_name,
            email=email,
            role=role,
            is_active=True,
            hashed_password=hashed,
            permissions={},
            assigned_projects=[]
        )
        save_user(new_user)
        return RedirectResponse("/admin?success=Usuario creado", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/admin?error={str(e)}", status_code=303)

@app.post("/admin/users/delete")
async def admin_delete_user(request: Request, email: str = Form(...)):
    try:
        delete_user(email)
        return RedirectResponse("/admin?success=Usuario eliminado", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/admin?error={str(e)}", status_code=303)

@app.post("/admin/projects/add")
async def admin_add_project(
    request: Request,
    name: str = Form(...),
    client: str = Form(""),
    amount: str = Form("0"),
    emoji: str = Form("📁"),
    category: str = Form("Residencial")
):
    try:
        amt_float = float(amount) if amount else 0.0
        create_project(
            name=name,
            client=client,
            amount=amt_float,
            emoji=emoji,
            status="Activo",
            category=category
        )
        return RedirectResponse("/admin?success=Proyecto creado", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/admin?error={str(e)}", status_code=303)

@app.post("/create_project")
async def staff_create_project(
    request: Request,
    name: str = Form(...),
    client: str = Form(""),
    amount: str = Form("0"),
    emoji: str = Form("📁"),
    status: str = Form("Activo"),
    root_path: str = Form(None) # Ignore legacy param
):
    try:
        amt_float = float(amount) if amount else 0.0
        create_project(
            name=name,
            client=client,
            amount=amt_float,
            emoji=emoji,
            status=status, 
            category="Residencial" # Default for now
        )
        return RedirectResponse("/projects", status_code=303)
    except Exception as e:
        print(f"Error creating project: {e}")
        return RedirectResponse(f"/projects?error={str(e)}", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/admin?error={str(e)}", status_code=303)

@app.get("/admin/backup/download")
async def download_database_backup(request: Request):
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "admin":
        return RedirectResponse("/")

    # Identify DB Type
    db_url = os.getenv("DATABASE_URL", "")
    
    # Filename
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    
    if "postgres" in db_url:
        filename = f"backup_ao_full_{timestamp}.sql"
        try:
            # Use pg_dump
            # PGPASSWORD env var is needed for non-interactive auth
            # URL parsing
            from urllib.parse import urlparse
            p = urlparse(db_url)
            
            # Construct pg_dump command
            # Using --no-owner --no-acl to avoid restore permission issues on different users
            cmd = ["pg_dump", "--no-owner", "--no-acl", "--clean", "--if-exists", db_url]
            
            # Run process
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Stream response
            return StreamingResponse(
                proc.stdout, 
                media_type="application/octet-stream", 
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        except Exception as e:
            print(f"Backup Error: {e}")
            return HTMLResponse(f"Error creating backup: {e}", status_code=500)
            
    else:
        # Fallback to SQLite (Local)
        filename = f"backup_ao_local_{timestamp}.db"
        db_path = "sql_app.db" # Default local
        if os.path.exists(db_path):
            return FileResponse(db_path, filename=filename)
        else:
            return HTMLResponse("Database file not found (Local)", status_code=404)

@app.get("/admin/files/download")
async def download_files_backup(request: Request):
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "admin":
        return RedirectResponse("/")

    import zipfile
    from io import BytesIO

    memory_file = BytesIO()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"backup_ao_files_{timestamp}.zip"

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Define folders that store user uploaded content
        folders_to_zip = ["Collaborators", "Projects", "Expenses"]
        
        for folder_name in folders_to_zip:
             folder_path = os.path.abspath(folder_name)
             if os.path.exists(folder_path):
                 for root, dirs, files in os.walk(folder_path):
                     for file in files:
                         file_path = os.path.join(root, file)
                         # Create relative path for the zip archive
                         # This preserves the folder structure (e.g., Projects/123/file.pdf)
                         try:
                             arcname = os.path.relpath(file_path, os.getcwd())
                             zf.write(file_path, arcname)
                         except Exception as ie:
                             print(f"Skipping file {file}: {ie}")
    
    memory_file.seek(0)
    return StreamingResponse(
        memory_file, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

# CATCH ALL FOR STATIC SITE ASSETS
@app.get('/{file_path:path}')
async def serve_static_root(file_path: str):
    if '..' in file_path: return JSONResponse({'error': 'Invalid path'}, status_code=400)
    
    # Use BASE_DIR for absolute path resolution
    path = os.path.join(BASE_DIR, 'static/public_site', file_path)
    
    if os.path.exists(path) and os.path.isfile(path):
        # Explicitly handle common MIME types if needed (though FileResponse usually does well)
        media_type = None
        if path.endswith(".css"): media_type = "text/css"
        if path.endswith(".js"): media_type = "application/javascript"
        return FileResponse(path, media_type=media_type)
        
    print(f"CATCH ALL REDIRECT: {file_path} -> /")
    # Redirect 404s to Home (Landing Page)
    # Use 302 to distinguish from Auth(303) and Default(307)
    return RedirectResponse("/", status_code=302)

@app.get("/knowledge", response_class=HTMLResponse)
async def knowledge_page(request: Request):
    return templates.TemplateResponse("knowledge_base.html", {"request": request})

