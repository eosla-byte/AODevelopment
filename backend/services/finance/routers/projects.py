from fastapi import APIRouter, Request, Form, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import os
import shutil
import datetime
from common.database import (
    get_projects, create_project, get_project_details, update_project_meta,
    update_project_collaborators, get_total_collaborator_allocations,
    update_project_profit_config, add_partner_withdrawal, update_project_file_meta,
    delete_project_file_meta, add_project_reminder, delete_project_reminder,
    toggle_project_reminder, get_market_studies, add_market_study, delete_market_study,
    get_collaborators, get_project_stats_by_category
)
from common.auth import require_service

router = APIRouter(
    tags=["Projects"]
)

# Template Setup
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

# --- Projects List ---
@router.get("/projects", response_class=HTMLResponse)
async def read_projects(request: Request):
    projects = get_projects()
    
    # --- Project Grouping Logic ---
    grouped_items = []
    groups = {} 
    singles = []
    
    for p in projects:
        if '-' in str(p.id):
            parts = str(p.id).split('-')
            prefix = parts[0]
            if len(prefix) >= 3:
                if prefix not in groups: groups[prefix] = []
                groups[prefix].append(p)
                continue
        singles.append(p)
        
    for prefix, proj_list in groups.items():
        if len(proj_list) > 1:
            proj_list.sort(key=lambda x: x.id)
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
                "status": "Varios",
                "start_date": proj_list[0].start_date
            }
            grouped_items.append(group_obj)
        else:
            singles.append(proj_list[0])
            
    grouped_items.extend(singles)
    
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "items": grouped_items
    })

# --- Project Detail ---
@router.get("/project/{project_id}", response_class=HTMLResponse)
async def read_project(request: Request, project_id: str):
    try:
        project = get_project_details(project_id)
        if not project:
            return RedirectResponse("/projects")
            
        return templates.TemplateResponse("project_detail.html", {
            "request": request,
            "p": project,
            "collaborators": get_collaborators(),
            "total_allocations": get_total_collaborator_allocations()
        })
    except Exception as e:
        import traceback
        return HTMLResponse(content=f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>", status_code=500)

@router.post("/project/{project_id}/edit")
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
    acc_hub: str = Form(""),
    acc_project: str = Form(""),
    acc_folder: str = Form(""),
    acc_file: str = Form("")
):
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

@router.post("/project/{project_id}/delete")
async def delete_project(project_id: str):
    project = get_project_details(project_id)
    if project:
        update_project_meta(
            project_id,  
            project.client, project.status, project.nit, project.legal_name, project.po_number,
            project.amount, project.emoji, project.start_date, project.duration_months,
            project.additional_time_months, project.paid_amount, project.square_meters, category=project.category,
            archived=True 
        )
    return RedirectResponse("/projects", status_code=303)

@router.post("/project/{project_id}/restore")
async def restore_project(project_id: str):
    project = get_project_details(project_id)
    if project:
        update_project_meta(
            project_id,  
            project.client, project.status, project.nit, project.legal_name, project.po_number,
            project.amount, project.emoji, project.start_date, project.duration_months,
            project.additional_time_months, project.paid_amount, project.square_meters, category=project.category,
            archived=False 
        )
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@router.post("/project/{project_id}/collaborators/update")
async def update_collaborators_route(project_id: str, request: Request):
    try:
        assignments = await request.json()
        update_project_collaborators(project_id, assignments)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error updating collaborators: {e}")
        return {"status": "error", "message": str(e)}

# --- Reminders ---
@router.post("/project/{project_id}/reminder/add")
async def add_reminder(project_id: str, title: str = Form(...), date: str = Form(...), frequency: str = Form("Once")):
    add_project_reminder(project_id, title, date, frequency)
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@router.post("/project/{project_id}/reminder/delete")
async def delete_reminder(project_id: str, reminder_id: str = Form(...), redirect_to: str = Form(None)):
    delete_project_reminder(project_id, reminder_id)
    if redirect_to and redirect_to == "calendar":
         return RedirectResponse("/calendar", status_code=303)
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@router.post("/project/{project_id}/reminder/toggle")
async def toggle_reminder(project_id: str, reminder_id: str = Form(...)):
    toggle_project_reminder(project_id, reminder_id)
    return RedirectResponse(f"/project/{project_id}", status_code=303)

# --- Profit & Withdrawals ---
@router.post("/project/{project_id}/profit/update")
async def update_profit_config_route(
    project_id: str,
    projected_margin: str = Form("0.0"),
    real_margin: str = Form("0.0"),
    request: Request = None
):
    form = await request.form()
    partners_config = {}
    
    for key, value in form.items():
        if key.startswith("partner_share_"):
            collab_id = key.replace("partner_share_", "")
            try: partners_config[collab_id] = float(value)
            except: pass
                
    try: p_margin = float(projected_margin)
    except: p_margin = 0.0
    
    try: r_margin = float(real_margin)
    except: r_margin = 0.0
    
    update_project_profit_config(project_id, p_margin, r_margin, partners_config)
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@router.post("/project/{project_id}/withdrawal/add")
async def add_withdrawal(project_id: str, collab_id: str = Form(...), amount: str = Form(...), note: str = Form("")):
    try:
        amt = float(amount)
        add_partner_withdrawal(project_id, collab_id, amt, note)
    except: pass
    return RedirectResponse(f"/project/{project_id}", status_code=303)

# --- Files ---
@router.get("/project_file/{project_id}/{category}/{filename}")
async def serve_project_file(project_id: str, category: str, filename: str):
    project = get_project_details(project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
        
    target_dir = os.path.join(os.path.abspath("Projects"), project.id, category)
    file_path = os.path.join(target_dir, filename)
    
    if not os.path.exists(file_path):
        return HTMLResponse("File not found", status_code=404)
        
    return FileResponse(file_path)

@router.post("/project/{project_id}/upload")
async def upload_file(project_id: str, category: str = Form(...), amount: str = Form(None), note: str = Form(""), file_date: str = Form(None), file: UploadFile = File(...)):
    project = get_project_details(project_id)
    if project:
        target_dir = os.path.join(os.path.abspath("Projects"), project.id, category)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        file_path = os.path.join(target_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        val = 0.0
        if amount and amount.strip():
             try: val = float(amount)
             except: pass
             
        try:
             final_note = note if note and note.strip() else "" 
             update_project_file_meta(project_id, category, file.filename, val, final_note, file_date)
        except Exception as e:
             print(f"ERROR: Failed to save metadata during upload: {e}")
             pass
            
    return RedirectResponse(f"/project/{project_id}", status_code=303)

@router.post("/project/{project_id}/file/delete")
async def delete_file(project_id: str, category: str = Form(...), filename: str = Form(...)):
    project = get_project_details(project_id)
    if project:
        file_path = os.path.join(os.path.abspath("Projects"), project.id, category, filename)
        if os.path.exists(file_path):
             os.remove(file_path)
             delete_project_file_meta(project_id, category, filename)
             
    return RedirectResponse(f"/project/{project_id}", status_code=303)

# --- Calendar ---
@router.get("/calendar", response_class=HTMLResponse)
async def read_global_calendar(request: Request):
    projects = get_projects()
    return templates.TemplateResponse("calendar.html", {
        "request": request, 
        "projects": projects,
        "current_month_name": datetime.datetime.now().strftime("%B")
    })

# --- Cotizador ---
@router.get("/cotizador", response_class=HTMLResponse)
async def read_cotizador(request: Request):
    try:
        projects = get_projects()
        market_studies = get_market_studies()
        
        for p in projects:
            assigned = getattr(p, 'assigned_collaborators', {})
            if not isinstance(assigned, dict): assigned = {}
            p.collab_count = len(assigned)
            
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
        return HTMLResponse(content=f"Error: {e}", status_code=500)

@router.post("/cotizador/market/add")
async def add_market_study_route(
    name: str = Form(...),
    amount: float = Form(...),
    square_meters: float = Form(...),
    months: float = Form(...),
    category: str = Form(...)
):
    add_market_study(name, amount, square_meters, months, category)
    return RedirectResponse("/cotizador", status_code=303)

@router.post("/cotizador/market/delete")
async def delete_market_study_route(study_id: str = Form(...)):
    delete_market_study(study_id)
    return RedirectResponse("/cotizador", status_code=303)

@router.post("/create_project")
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
    create_project(name, client, nit, legal_name, po_number, amount, status, emoji, custom_id)
    return RedirectResponse(url="/projects", status_code=303)

