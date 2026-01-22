from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import uuid
import json

router = APIRouter(prefix="/api/plugin/sheets", tags=["Sheets"])


from database import create_sheet_session, get_sheet_session, queue_command

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
        updates = data.get("updates") # ordered list of { id, number, name, params }
        
        # We need to know WHICH plugin session to target.
        session_data = get_sheet_session(session_id)
        if not session_data:
             return JSONResponse({"status": "error", "message": "Session expired"}, status_code=404)
             
        plugin_session_id = session_data.get("plugin_session_id")
        
        if not plugin_session_id:
             return JSONResponse({"status": "error", "message": "Plugin Link Lost"}, status_code=400)
        
        # Queue Command for the specific Plugin Session
        queue_command(plugin_session_id, "UPDATE_SHEETS", updates)
        
        return JSONResponse({"status": "ok"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# --- TEMPLATES ---
from database import get_sheet_templates, create_sheet_template, delete_sheet_template

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
