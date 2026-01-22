from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import uuid
import json

router = APIRouter(prefix="/api/plugin/sheets", tags=["Sheets"])

# Quick in-memory store for sessions (for Beta)
# Stores { session_id: { project_name: str, sheets: [], param_defs: [] } }
SHEET_SESSIONS = {}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@router.post("/init")
async def init_sheet_session(request: Request):
    """
    Receives Sheet Data Dump from Revit Plugin
    """
    try:
        data = await request.json()
        session_id = str(uuid.uuid4())
        
        SHEET_SESSIONS[session_id] = {
            "project": data.get("project", "Unknown Project"),
            "sheets": data.get("sheets", []),
            "param_definitions": data.get("param_definitions", []),
            "plugin_session_id": data.get("plugin_session_id")
        }
        
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
    data = SHEET_SESSIONS.get(session_id)
    if not data:
        return JSONResponse({"status": "error", "message": "Session expired"}, status_code=404)
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
        # The user session is stored in memory SHEET_SESSIONS
        if session_id not in SHEET_SESSIONS:
             return JSONResponse({"status": "error", "message": "Session expired"}, status_code=404)
             
        session_data = SHEET_SESSIONS[session_id]
        plugin_session_id = session_data.get("plugin_session_id")
        
        if not plugin_session_id:
             return JSONResponse({"status": "error", "message": "Plugin Link Lost"}, status_code=400)
        
        from database import queue_command
        
        # Queue Command for the specific Plugin Session
        # Payload must match what VisualizerHandler expects: { action, payload } (implicit in queue_command?)
        # queue_command(session_id, action, payload)
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
