from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/plugin/cloud",
    tags=["Plugin Cloud Logic (Level 3 Security)"]
)

# Request Models
class GeometryPayload(BaseModel):
    project_id: str
    element_type: str # e.g., 'Wall', 'Floor'
    vertices: List[Dict[str, float]] # [{'x':0.0, 'y':0.0, 'z':0.0}, ...]
    metadata: Dict[str, Any]

class CalculationResult(BaseModel):
    volume: float
    area: float
    status: str
    message: str

@router.post("/calculate/quantities", response_model=CalculationResult)
async def calculate_quantities_cloud(payload: GeometryPayload):
    """
    Cloud-based calculation endpoint.
    The logic here is protected on the server.
    """
    # 1. Verify User/License (Ideally via Dependency)
    # verify_license(request) ...
    
    print(f"Received Cloud Logic Request for {payload.element_type}")
    
    # 2. Perform proprietary calculation
    # (Placeholder logic)
    # real_volume = convex_hull_volume(payload.vertices) ...
    
    calculated_volume = 0.0
    calculated_area = 0.0
    
    # Heuristic demo
    if payload.vertices:
        calculated_area = len(payload.vertices) * 1.5 # Fake math
        calculated_volume = calculated_area * 3.0
        
    return CalculationResult(
        volume=calculated_volume,
        area=calculated_area,
        status="Success",
        message="Calculated securely in cloud"
    )

# ==========================================
# COMMAND QUEUE (BRIDGE)
# ==========================================
# Replaced In-Memory with DB Queue to handle multiple workers (Gunicorn)
from database import queue_command, get_pending_commands

class CommandPayload(BaseModel):
    action: str
    payload: Dict[str, Any]

@router.post("/command/{session_id}")
async def send_command_to_revit(session_id: str, cmd: CommandPayload):
    queue_command(session_id, cmd.action, cmd.payload)
    return {"status": "queued"}

@router.get("/commands/{session_id}")
async def get_commands_for_revit(session_id: str):
    cmds = get_pending_commands(session_id)
    return {"commands": cmds}

# ==========================================
# CLOUD QUANTIFY SYNC
# ==========================================

# In-Memory Session Store (For now, could be DB backed later)
from database import save_cloud_session, get_cloud_session, list_cloud_projects, delete_cloud_session, create_project_folder, list_project_folders, delete_project_folder

class CloudQuantifyPayload(BaseModel):
    session_id: str
    project_name: str
    user_email: str
    folder_id: str = None # Optional folder assignment
    data: Dict[str, Any]

@router.post("/sync-quantities")
async def sync_quantities(payload: CloudQuantifyPayload):
    """
    Receives broad quantification data from Revit.
    Stores and persists in DB.
    """
    print(f"Received Cloud Sync from {payload.user_email} for {payload.project_name}")
    
    # Save to DB
    # We construct the initial data state.
    # We assume 'data' is the Revit Data.
    # The session might already exist if re-syncing.
    
    # We need to preserve existing 'cards/sheets' if session exists?
    # Usually a Sync overwrites the 'REVIT_DATA' part but SHOULD keep user cards/sheets?
    # Current implementation in JS: loadSessionData overwrites REVIT_DATA but uses payload.savedData for cards.
    # Let's see if payload has 'cards'. No, CloudQuantifyPayload just has 'data' (Revit dump).
    
    # Check existing session
    existing = get_cloud_session(payload.session_id)
    final_data = {}
    
    if existing:
        final_data = existing["data"]
        final_data["data"] = payload.data # Update Revit Data part
    else:
        final_data = {
            "data": payload.data, # Revit Data
            "cards": [],
            "groups": [],
            "sheets": []
        }
        
    # If folder_id provided, ensure session is linked
    res = save_cloud_session(payload.session_id, final_data, payload.project_name, payload.user_email, payload.folder_id)
    
    if res:
        return {"status": "success", "session_id": payload.session_id, "message": "Data synced and saved to DB"}
    return {"status": "error", "message": "DB Error"}

class ProjectSavePayload(BaseModel):
    session_id: str
    project_name: str
    cards: list
    groups: list
    sheets: list

@router.post("/save-project")
async def save_project(payload: ProjectSavePayload):
    # Get existing to preserve Revit Data
    existing = get_cloud_session(payload.session_id)
    if not existing:
         return {"status": "error", "message": "Session not found to update"}
         
    current_data = existing["data"]
    
    # Update managed parts
    current_data["cards"] = payload.cards
    current_data["groups"] = payload.groups
    current_data["sheets"] = payload.sheets
    
    # Save
    res = save_cloud_session(payload.session_id, current_data, payload.project_name)
    
    if res:
        return {"status": "success", "message": "Project saved to DB"}
    return {"status": "error", "message": "DB Save Error"}

@router.get("/list-projects")
async def list_projects_endpoint():
    # In future, filter by user from token
    projects = list_cloud_projects()
    # Transform to match frontend expectation if needed
    # Frontend expects: { projects: [ {name, session_id, updated}, ... ] }
    # list_cloud_projects returns matches that structure.
    return {"projects": projects}

@router.post("/archive-project")
async def archive_project_endpoint(session_id: str):
    success = delete_cloud_session(session_id)
    if success:
        return {"status": "success", "message": "Project archived/deleted"}
    return {"status": "error", "message": "Could not delete project"}

# --- FOLDER ROUTES ---

class CreateFolderPayload(BaseModel):
    name: str

@router.post("/create-folder")
async def create_folder_endpoint(payload: CreateFolderPayload):
    new_id = create_project_folder(payload.name)
    if new_id:
        return {"status": "success", "folder_id": new_id, "message": "Folder created"}
    return {"status": "error", "message": "Failed to create folder"}

@router.get("/list-folders")
async def list_folders_endpoint():
    folders = list_project_folders()
    return {"folders": folders}

@router.post("/delete-folder")
async def delete_folder_endpoint(folder_id: str = Body(..., embed=True)):
    # embed=True expects JSON {folder_id: "..."}
    success = delete_project_folder(folder_id)
    if success:
        return {"status": "success", "message": "Folder deleted"}
    return {"status": "error", "message": "Failed to delete folder"}

@router.post("/rename-folder")
async def rename_folder_endpoint(folder_id: str = Body(..., embed=True), new_name: str = Body(..., embed=True)):
    # Imports inside to avoid circular dependency issues if any, or ensuring they are available.
    # We need to update the import at top of file, but for now assuming these will be available via 'database' module import.
    from database import rename_project_folder
    success = rename_project_folder(folder_id, new_name)
    if success:
        return {"status": "success", "message": "Folder renamed"}
    return {"status": "error", "message": "Failed to rename folder"}

@router.post("/rename-session")
async def rename_session_endpoint(session_id: str = Body(..., embed=True), new_name: str = Body(..., embed=True)):
    from database import rename_cloud_session
    success = rename_cloud_session(session_id, new_name)
    if success:
        return {"status": "success", "message": "Session renamed"}
    return {"status": "error", "message": "Failed to rename session"}

@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    """
    Retrieves the stored session data for the Web UI.
    """
    data = get_cloud_session(session_id)
    if data:
        # Frontend logic expects 'data' key to be the Revit Data?
        # Let's check frontend.
        # Frontend: payload = await response.json(); REVIT_DATA = payload.data;
        # And it checks payload.savedData for cards.
        
        # We need to map our DB structure (flat JSON) to what frontend expects or update frontend.
        # DB JSON: { data: REVIT_DATA, cards: [], ... }
        # Frontend expects: { data: REVIT_DATA, savedData: { cards: ... }, project_name: ... }
        
        # Let's restructure response to match Legacy Frontend expectation to minimize frontend rewrites,
        # OR update frontend.
        # Let's transform here.
        
        inner_json = data["data"] # { data: ..., cards: [], ... }
        
        response_obj = {
            "session_id": data["session_id"],
            "project_name": data["project_name"],
            "user_email": data["user_email"],
            "data": inner_json.get("data"), # The Revit Data
            "savedData": {
                "cards": inner_json.get("cards", []),
                "groups": inner_json.get("groups", []),
                "sheets": inner_json.get("sheets", [])
            },
            "timestamp": data["timestamp"]
        }
        return response_obj
    
    raise HTTPException(status_code=404, detail="Session not found")
