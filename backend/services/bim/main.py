
from fastapi import FastAPI, Request, Depends, HTTPException, status, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
import uvicorn
import os
import sys
import uuid
import datetime

# Path Setup to allow importing 'backend.common'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_ROOT not in sys.path:
    sys.path.append(BACKEND_ROOT)

from common.database import get_db, SessionExt 
# Note: For this service, get_db should ideally point to SessionExt or we explicitely use SessionExt
from common.auth_utils import decode_access_token
from common.models import BimUser, BimOrganization, BimProject, BimScheduleVersion, BimActivity
from schedule_parser import parse_schedule

from routers import auth

app = FastAPI(title="AO PlanSystem (BIM Portal)")

# Mount Static if needed (Shared assets or dedicated?)
# For now, we can use CDN for tailwind, or mount shared if we want logos
# app.mount("/static", StaticFiles(directory=os.path.join(BACKEND_ROOT, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Include Routers
app.include_router(auth.router)

# Dependencies
def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        scheme, _, param = token.partition(" ")
        payload = decode_access_token(param)
        if not payload: return None
        return payload # Returns dict {"sub": email, "role": role, "org": org_id}
    except:
        return None

@app.get("/", response_class=HTMLResponse)
async def root(user = Depends(get_current_user)):
    if user:
        return RedirectResponse("/dashboard")
    return RedirectResponse("/auth/login")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/auth/login")
        
    # Fetch Org Name details?
    db = SessionExt()
    user_db = db.query(BimUser).filter(BimUser.email == user["sub"]).first()
    org_name = "Organización"
    if user_db and user_db.organization:
        org_name = user_db.organization.name
    db.close()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user_name": user.get("sub"), # Or Full Name if in token/db
        "user_initials": user.get("sub")[:2].upper(),
        "org_name": org_name
    })

@app.post("/projects/{project_id}/schedule/upload")
async def upload_schedule(project_id: str, file: UploadFile = File(...), user = Depends(get_current_user)):
    if not user: return RedirectResponse("/auth/login")
    
    # 1. Read File
    content = await file.read()
    
    try:
        # 2. Parse (Simulated)
        schedule_data = parse_schedule(content, file.filename)
        
        # 3. Save Version (Basic Implementation)
        db = SessionExt()
        
        new_version = BimScheduleVersion(
            id=str(uuid.uuid4()),
            project_id=project_id,
            version_name=f"Import {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            source_filename=file.filename,
            source_type=file.filename.split('.')[-1].upper(),
            imported_by=user['sub'] # Ideally ID
        )
        db.add(new_version)
        db.commit()
        
        # 4. Save Activities (Mock Loop)
        # for act in schedule_data['activities']: ...
        
        db.close()
        
        return {"status": "ok", "message": "Schedule imported successfully"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
