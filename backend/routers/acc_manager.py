from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Optional
import os
import shutil
from pydantic import BaseModel

import sys
import os

# Add tool directory to path dynamically
current_dir = os.path.dirname(os.path.abspath(__file__)) # .../routers
parent_dir = os.path.dirname(current_dir) # .../backend or /app
# Add tool directory to path dynamically
current_dir = os.path.dirname(os.path.abspath(__file__)) # .../routers
parent_dir = os.path.dirname(current_dir) # .../backend or /app
tools_path = os.path.join(parent_dir, "tools")

if tools_path not in sys.path:
    sys.path.append(tools_path)

try:
    # Import as package to support relative imports inside the tool
    from acc_copy_tool.copier import AccCopier
    from acc_copy_tool.auth import get_access_token
except ImportError as e:
    # Fallback or detailed error
    try:
        # Fallback for local dev where tools might be in root backend/tools and not picked up by logic above if cwd is weird
        from backend.tools.acc_copy_tool.copier import AccCopier
        from backend.tools.acc_copy_tool.auth import get_access_token
    except ImportError:
        raise ImportError(f"Could not import 'acc_copy_tool' package from {tools_path}. Error: {e}. Sys path: {sys.path}")

router = APIRouter(
    prefix="/api/labs/acc",
    tags=["AO Labs - Cloud Manager"]
)

# Helper to get copier instance (could be dependency)
def get_copier():
    try:
        return AccCopier()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ACC Config Error: {str(e)}")

# --- Endpoints ---

@router.get("/hubs")
def list_hubs():
    copier = get_copier()
    return copier.get_hubs()

@router.get("/hubs/{hub_id}/projects")
def list_projects(hub_id: str):
    copier = get_copier()
    return copier.get_projects(hub_id)

@router.get("/projects/{project_id}/top-folders")
def list_top_folders(hub_id: str, project_id: str):
    # API requires hub_id for top folders endpoint url structure usually?
    # Copier implementation uses it using hub_id.
    copier = get_copier()
    return copier.get_top_folders(hub_id, project_id)

@router.get("/projects/{project_id}/folders/{folder_id}/contents")
def list_contents(project_id: str, folder_id: str):
    copier = get_copier()
    folders, items = copier.get_folder_contents(project_id, folder_id)
    return {"folders": folders, "items": items}

# --- Create Folder ---

class CreateFolderPayload(BaseModel):
    project_id: str
    parent_id: str
    name: str

@router.post("/folders")
def create_new_folder(payload: CreateFolderPayload):
    copier = get_copier()
    res = copier.create_folder(payload.project_id, payload.parent_id, payload.name)
    if not res:
        raise HTTPException(status_code=500, detail="Failed to create folder")
    return {"status": "success", "data": res}


class CopyPayload(BaseModel):
    project_id: str
    source_id: str # Folder or Item ID
    target_parent_id: str
    is_folder: bool = False

@router.post("/action/copy")
def copy_content(payload: CopyPayload):
    copier = get_copier()
    if payload.is_folder:
        # Full Recursive Copy
        # 1. Fetch Source Folder Details
        source_folder = copier.get_folder(payload.project_id, payload.source_id)
        if not source_folder:
            raise HTTPException(status_code=404, detail="Source folder not found")
            
        # 2. Perform Recursive Copy
        try:
            copier.recursive_copy(payload.project_id, source_folder, payload.target_parent_id)
            return {"status": "success", "message": "Recursive copy started/completed"}
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Copy Error: {str(e)}")

    else:
        # Single File Copy
        res = copier.copy_item(payload.project_id, payload.source_id, payload.target_parent_id)
        if not res:
            raise HTTPException(status_code=500, detail="Copy failed")
        return {"status": "success", "data": res}

# --- File Upload (Basic) ---
# For direct browser upload to ACC, we usually need Signed URLs (OSS).
# Implementing 3-legged or 2-legged upload flow here.
# Step 1: Create Storage Object (POST projects/.../storage)
# Step 2: Upload to signed URL.
# Step 3: Create Item/Version.

@router.post("/upload")
def upload_file_to_acc(
    project_id: str = Form(...),
    folder_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Receives file from browser, uploads to ACC 
    (Proxy Upload: Browser -> Backend -> ACC).
    Limit: Good for files < 100MB.
    Run as SYNC function (def) so FastAPI uses threadpool.
    """
    copier = get_copier()
    
    # 1. Save temp
    temp_path = f"tmp_{file.filename}"
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        # 2. Upload Logic
        res = copier.upload_file(project_id, folder_id, temp_path, file.filename)
        if not res:
            # Should not happen if copier raises exception, but for safety:
            raise HTTPException(status_code=500, detail="Failed to upload (Unknown Error)")
        return {"status": "success", "data": res}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    return {"status": "implemented_soon"}
