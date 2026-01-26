from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import uuid
import json

router = APIRouter(prefix="/api/plugin/sheets", tags=["Sheets"])


from common.database import create_sheet_session, get_sheet_session, queue_command

@router.post("/init")
async def init_sheet_session(request: Request):
    """
    Receives Sheet Data Dump from Revit Plugin
    """
    try:
        data = await request.json()
        session_id = str(uuid.uuid4())
        
        project = data.get("project", "Unknown Project")
        sheets = data.get("sheets", [])
        param_defs = data.get("param_definitions", [])
        plugin_session_id = data.get("plugin_session_id")
        
        # Metadata Handing (Piggyback on sheets_json to avoid schema migration)
        browser_schemes = data.get("browser_schemes", [])
        title_blocks = data.get("title_blocks", [])

        # Wrap in V2 structure if metadata exists
        storage_payload = {
            "version": "v2",
            "sheets": sheets,
            "browser_schemes": browser_schemes,
            "title_blocks": title_blocks
        }
        
        # Persist to DB
        success = create_sheet_session(session_id, project, storage_payload, param_defs, plugin_session_id)
        
        if not success:
             return JSONResponse({"status": "error", "message": "Database Error"}, status_code=500)
        
        # Return redirect URL for Plugin to open
        return JSONResponse({
            "status": "ok",
            "session_id": session_id,
            "redirect_url": f"https://aodevelopment-production.up.railway.app/sheets/manager?session_id={session_id}"
        })
    except Exception as e:
        print(f"Error init sheets: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    data = get_sheet_session(session_id)
    if not data:
        return JSONResponse({"status": "error", "message": "Session expired or not found"}, status_code=404)
    return JSONResponse({"status": "ok", "data": data})

@router.post("/apply")
async def apply_sheet_changes(request: Request):
    """
    Receives updated Sheet List from Web UI
    Saves it to a Command Queue for Revit to poll
    """
    try:
        data = await request.json()
        session_id = data.get("session_id")
        updates = data.get("updates") 
        
        print(f"DEBUG Apply: Received {len(updates)} updates for session {session_id}")
        
        # We need to know WHICH plugin session to target.
        session_data = get_sheet_session(session_id)
        if not session_data:
             print("DEBUG Apply: Session Expired/Not Found")
             return JSONResponse({"status": "error", "message": "Session expired"}, status_code=404)
             
        plugin_session_id = session_data.get("plugin_session_id")
        print(f"DEBUG Apply: Target Plugin Session {plugin_session_id}")
        
        # AGGRESSIVE RECOVERY: Check if session is alive
        from common.database import get_session_by_id, get_latest_active_session, update_sheet_session_plugin_id
        import datetime
        
        current_plugin_session = get_session_by_id(plugin_session_id)
        
        # Determine if stale (older than 2 mins or missing)
        is_stale = False
        if not current_plugin_session:
            is_stale = True
        else:
            cutoff = datetime.datetime.now() - datetime.timedelta(minutes=2)
            if current_plugin_session.last_heartbeat < cutoff:
                is_stale = True
                
        if is_stale:
            # Try to heal
            user_email = current_plugin_session.user_email if current_plugin_session else None
            machine_id = current_plugin_session.machine_id if current_plugin_session else None
            
            if user_email or machine_id:
                new_session = get_latest_active_session(user_email, machine_id)
                if new_session:
                    print(f"Session Healed! Old: {plugin_session_id} -> New: {new_session.id}")
                    plugin_session_id = new_session.id
                    # Update DB for future calls
                    update_sheet_session_plugin_id(session_id, plugin_session_id)
                else:
                    return JSONResponse({"status": "error", "message": "No active Revit session found for user. Please check Revit."}, status_code=400)
            else:
                 return JSONResponse({"status": "error", "message": "Original Revit Link Lost. Please re-open from Revit."}, status_code=400)
        
        if not plugin_session_id:
             return JSONResponse({"status": "error", "message": "Plugin Link Lost"}, status_code=400)
        
        # Queue Command for the specific Plugin Session
        # Targeted Command - No Broadcast
        queue_command(plugin_session_id, "UPDATE_SHEETS", updates)
        
        return JSONResponse({"status": "ok", "message": "Command Queued (Targeted)"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# --- TEMPLATES ---
from common.database import get_sheet_templates, create_sheet_template, delete_sheet_template

@router.get("/templates")
async def list_sheet_templates():
    tpls = get_sheet_templates()
    # Serialize
    return JSONResponse({"status": "ok", "templates": [
        {"id": t.id, "name": t.name, "config": t.config_json, "created_by": t.created_by} for t in tpls
    ]})

@router.post("/templates")
async def save_sheet_template(request: Request):
    try:
        data = await request.json()
        name = data.get("name")
        config = data.get("config")
        user = data.get("user", "Admin") # In future get from token
        
        if not name or not config:
            return JSONResponse({"status": "error", "message": "Missing name or config"}, status_code=400)
            
        tpl = create_sheet_template(name, config, user)
        if tpl:
            return JSONResponse({"status": "ok", "template_id": tpl.id})
        return JSONResponse({"status": "error", "message": "DB Error"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@router.delete("/templates/{id}")
async def delete_template_endpoint(id: int):
    success = delete_sheet_template(id)
    if success: return JSONResponse({"status": "ok"})
    return JSONResponse({"status": "error", "message": "Not found"}, status_code=404)

@router.get("/status")
async def check_connection_status(session_id: str):
    """
    Returns the health of the Revit Link.
    """
    from common.database import get_sheet_session # Ensure imports
    session_data = get_sheet_session(session_id)
    if not session_data:
        return {"status": "error", "message": "Session Not Found"}
    
    plugin_session_id = session_data.get("plugin_session_id")
    if not plugin_session_id:
        return {"status": "disconnected", "message": "No Revit Link"}
        
    from common.database import get_session_by_id, get_pending_commands
    import datetime
    
    ps = get_session_by_id(plugin_session_id)
    if not ps:
        return {"status": "disconnected", "message": "Revit Session Lost"}
        
    # Check Age
    age = (datetime.datetime.now() - ps.last_heartbeat).total_seconds()
    is_alive = age < 60 # 1 minute threshold
    
    # Check Queue
    pending = get_pending_commands(plugin_session_id) # returns list
    queue_size = len(pending)
    
    return {
        "status": "connected" if is_alive else "stale",
        "age_seconds": int(age),
        "queue_size": queue_size,
        "machine": ps.machine_id,
        "user": ps.user_email
    }
@router.get("/logs")
async def get_logs_endpoint(session_id: str):
    from common.database import get_sheet_session, get_session_logs
    
    session_data = get_sheet_session(session_id)
    if not session_data:
        return {"status": "error", "message": "Session Not Found"}
        
    plugin_session_id = session_data.get("plugin_session_id")
    if not plugin_session_id:
        return {"logs": []}
        
    logs = get_session_logs(plugin_session_id)
    return {"status": "ok", "logs": logs}
