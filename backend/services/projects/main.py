from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import os

from ...common.database import get_projects, create_project, get_project_details
from ...common.models import Project

app = FastAPI(title="AO Projects")

# Templates (Shared for now, or specific?)
# Using shared templates from root 'backend/templates'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/list", response_class=JSONResponse)
async def api_list_projects():
    projects = get_projects()
    return projects

@app.post("/create")
async def create_project_endpoint(
    name: str = Form(...), 
    client: str = Form(""), 
    amount: float = Form(0.0),
    emoji: str = Form("📁")
):
    success = create_project(name=name, client=client, amount=amount, emoji=emoji)
    if success:
        return RedirectResponse("/projects", status_code=303)
    return JSONResponse({"error": "Failed"}, status_code=500)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AO Projects"}
