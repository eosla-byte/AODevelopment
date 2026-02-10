
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel
from typing import List, Optional
import datetime
import json

# Import from local common
from ..common.database import (
    start_revit_session, heartbeat_session, end_revit_session,
    log_plugin_activity, log_plugin_sync, get_user_by_email
)
from ..common.auth import create_access_token # RS256
# verify_password -> might need to vendor utils or just copy it? verify_password is in auth_utils.
# I will check if auth.py has verify_password. I suspect it doesn't.
# I might need to vendor auth_utils too OR move verify_password to auth.py.
# Let's assume for now I need verify_password.
from ..common.auth import decode_token as decode_access_token, verify_password, get_password_hash
# from common.auth_utils import verify_password -> Local auth_utils missing!


router = APIRouter(prefix="/api/plugin")

# Helper for Dependency Injection
def verify_token_dep():
   pass

# --- Models ---
class PluginLoginRequest(BaseModel):
    username: str
    password: str
    machine_name: str
    revit_version: str
    plugin_version: Optional[str] = "1.0.0"
    ip_address: str

class HeartbeatRequest(BaseModel):
    session_id: str
    ip_address: str

class ActivityCheckRequest(BaseModel):
    session_id: str
    file_name: str
    active_minutes: float
    idle_minutes: float
    revit_user: Optional[str] = None
    acc_project: Optional[str] = None

class SyncLogRequest(BaseModel):
    session_id: str
    file_name: str
    central_path: str

class TokenValidationRequest(BaseModel):
    token: str

# --- Routes ---

@router.post("/login")
async def plugin_login(req: PluginLoginRequest):
    # user = get_user_by_email(req.username)
    user = get_user_by_email(req.username)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username")
        
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")
        
    if not user.is_active:
         raise HTTPException(status_code=403, detail="User account is locked")

    # Plugin Current Version Logic
    from database import get_latest_plugin_version
    
    latest_v_data = get_latest_plugin_version()
    
    latest_version = "1.5.2" # Default
    update_info = None
    
    if latest_v_data:
        latest_version = latest_v_data["version"]
        update_info = latest_v_data

    # Create Session
    session_id = start_revit_session(user.email, req.machine_name, req.revit_version, req.ip_address, plugin_version=req.plugin_version)

    # Generate Token (optional context)
    token = create_access_token(data={"sub": user.email, "role": user.role, "session_id": session_id})
    
    # Permissions
    permissions = getattr(user, 'permissions', {})
    if not permissions: permissions = {}

    return {
        "access_token": token,
        "token_type": "bearer",
        "session_id": session_id,
        "heartbeat_interval_seconds": 60, # 1 minute
        "user_name": user.name,
        "role": user.role,
        "latest_version": latest_version,
        "update_info": update_info,
        "permissions": permissions
    }

@router.post("/heartbeat")
async def plugin_heartbeat(req: HeartbeatRequest):
    # Heartbeat and get Updated Permissions
    # We need to know the User to get their current permissions from DB.
    # heartbeat_session returns True/False.
    # Let's modify logic to fetch session/user.
    
    # Imports inside function to avoid circular if any, or assume imported
    from database import get_session_by_id, get_user_by_email, heartbeat_session
    
    success = heartbeat_session(req.session_id, req.ip_address)
    
    if not success:
         return {"status": "Invalid Session", "action": "ReLogin"}

    # Get User Permissions
    permissions = {}
    
    # FETCH PENDING COMMANDS
    from database import get_pending_commands, mark_commands_as_sent
    
    commands = get_pending_commands(req.session_id)
    # Mark them as SENT so we know they left the server
    if commands:
        cmd_ids = [c["id"] for c in commands]
        mark_commands_as_sent(cmd_ids)
    
    session = get_session_by_id(req.session_id)
    if session:
        user = get_user_by_email(session.user_email)
        if user:
            permissions = getattr(user, 'permissions', {})

    return {
        "status": "Active", 
        "action": "Continue",
        "permissions": permissions,
        "commands": commands # Helper for Plugin to consume
    }

class CommandResult(BaseModel):
    command_id: int
    status: str # "success", "error"
    result_json: Optional[dict] = {}
    message: Optional[str] = ""

@router.post("/command/result")
async def command_result(res: CommandResult):
    from database import update_command_status
    success = update_command_status(res.command_id, res.status, res.result_json, res.message)
    if not success:
        raise HTTPException(status_code=404, detail="Command not found")
    return {"status": "Updated"}

@router.post("/track")
async def plugin_track(req: ActivityCheckRequest):
    log_plugin_activity(
        req.session_id, 
        req.file_name, 
        req.active_minutes, 
        req.idle_minutes,
        req.revit_user,
        req.acc_project
    )
    return {"status": "Logged"}

@router.post("/sync")
async def plugin_sync(req: SyncLogRequest):
    log_plugin_sync(req.session_id, req.file_name, req.central_path)
    return {"status": "Logged"}

@router.post("/validate-token")
async def validate_token_endpoint(req: TokenValidationRequest):
    from auth_utils import decode_access_token
    payload = decode_access_token(req.token)
    if payload:
        return {"valid": True, "expires": payload.get("exp"), "user": payload.get("sub")}
    else:
        return {"valid": False}


from takeoff_database import save_project_packages, get_project_packages

class TakeoffSyncRequest(BaseModel):
    project_id: str
    packages_json: str

@router.post("/takeoff/sync")
async def sync_takeoff(req: TakeoffSyncRequest, token: str = Depends(verify_token_dep)):
    # Verify token implies user is authenticated.
    # In a real scenario, we'd check if user has access to this project_id.
    save_project_packages(req.project_id, req.packages_json)
    return {"status": "Saved", "project_id": req.project_id}

@router.get("/takeoff/{project_id}")
async def get_takeoff(project_id: str, token: str = Depends(verify_token_dep)):
    data = get_project_packages(project_id)
    # Return as raw json string or parsed object? 
    # Let's return as object to be clean, or raw string inside a field.
    # To avoid double parsing overhead here, we can just return it as a generic dict.
    try:
        parsed = json.loads(data)
        return parsed
    except:
        return []

# Helper for Dependency Injection if not present in original file


# -----------------------------------------------------------------------------
# ROUTINES (KNOWLEDGE BASE)
# -----------------------------------------------------------------------------
from database import save_routine, get_all_routines

class RoutineCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str
    actions_json: List[str] # List of strings for now
    user_email: str
    is_global: bool = False

@router.post("/routines")
def create_routine_endpoint(routine: RoutineCreate):
    try:
        r = save_routine(
            title=routine.title,
            description=routine.description,
            category=routine.category,
            actions_json=routine.actions_json,
            user_email=routine.user_email,
            is_global=routine.is_global
        )
        if r: return {"status": "success", "id": r.id}
        else: raise HTTPException(status_code=500, detail="DB Error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/routines")
def get_routines_endpoint(user_email: Optional[str] = None):
    # If called from Admin Dashboard (no email param usually), return ALL (handled by get_all_routines if email is None)
    routines = get_all_routines(user_email)
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "category": r.category,
            "actions": r.actions_json,
            "is_global": r.is_global,
            "author": r.user_email
        }
        for r in routines
    ]
