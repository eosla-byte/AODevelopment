from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
import shutil
import datetime
from common.database import (
    get_collaborators, create_collaborator, get_collaborator_details, 
    update_collaborator, update_collaborator_picture, add_adjustment, 
    remove_adjustment, toggle_archive_collaborator, save_payroll_close,
    calculate_isr_projection, get_months_worked, get_user_plugin_stats,
    get_user_plugin_logs, get_collaborator_assigned_projects
)

router = APIRouter(
    tags=["HR"]
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

@router.get("/hr", response_class=HTMLResponse)
async def read_hr(request: Request, view: str = "active"):
    collaborators = get_collaborators()
    
    # Active Operating Collabs for metrics (Activo + Not Archived)
    active_operating_collabs = [c for c in collaborators if getattr(c, 'status', 'Activo') == 'Activo' and not getattr(c, 'archived', False)]
    
    total_collabs = len(active_operating_collabs)
    monthly_payroll = sum(c.salary for c in active_operating_collabs)
    annual_payroll = monthly_payroll * 12 
    total_liability = sum(c.accumulated_liability for c in active_operating_collabs)
    total_employer_costs = sum((c.base_salary * (0.1067 + 0.01 + 0.01)) for c in active_operating_collabs)
    
    # Birthday Calendar
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
            except: pass
    birthdays.sort(key=lambda x: x['day'])
    
    # Filter
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
             
    if not grouped_collabs["Otros"]: del grouped_collabs["Otros"]

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

@router.get("/hr/{collab_id}", response_class=HTMLResponse)
async def read_hr_detail(request: Request, collab_id: str):
    try:
        collab = get_collaborator_details(collab_id)
        if not collab: return RedirectResponse("/hr")
            
        isr_projection = calculate_isr_projection(collab.base_salary, collab.bonus_incentive)
        
        adjs = collab.adjustments if hasattr(collab, 'adjustments') and collab.adjustments else []
        total_bonos = sum(float(a['amount']) for a in adjs if a['type'] == 'Bono')
        total_descuentos = sum(float(a['amount']) for a in adjs if a['type'] == 'Descuento')
        
        igss_laboral = collab.base_salary * 0.0483
        liquid_to_receive = (collab.base_salary + collab.bonus_incentive + total_bonos) - (igss_laboral + isr_projection + total_descuentos)
        
        months_worked = get_months_worked(collab.start_date)
        hist_total_earned = months_worked * (collab.base_salary + collab.bonus_incentive) 
        hist_employer_costs = months_worked * (collab.base_salary * (0.1067 + 0.01 + 0.01)) 
        hist_liability = months_worked * (collab.base_salary * (0.0833 + 0.0833 + 0.0417))
        
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
            "current_month_year": datetime.datetime.now().strftime("%Y-%m"),
            "next_month_name": (datetime.datetime.now() + datetime.timedelta(days=32)).strftime("%B"),
            "next_month_year": (datetime.datetime.now() + datetime.timedelta(days=32)).strftime("%Y-%m")
        }
        
        plugin_stats = get_user_plugin_stats(collab.email)
        calc_data["plugin_stats"] = plugin_stats
        
        assigned_projects = get_collaborator_assigned_projects(collab_id)
    
        return templates.TemplateResponse("hr_detail.html", {
            "request": request, 
            "c": collab,
            "calc": calc_data,
            "assigned_projects": assigned_projects
        })
    except Exception as e:
        import traceback
        return HTMLResponse(f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>", status_code=500)

@router.post("/hr/create")
async def create_hr(name: str = Form(...), role: str = Form("Collaborator"), salary: str = Form("0"), birthday: str = Form(""), start_date: str = Form("")):
    try: salary_float = float(salary) if salary and salary.strip() else 0.0
    except: salary_float = 0.0
    create_collaborator(name, role, salary_float, birthday, start_date)
    return RedirectResponse("/hr", status_code=303)

@router.post("/hr/{collab_id}/update")
async def update_hr_details(collab_id: str, 
                            role: str = Form("Collaborator"), 
                            base_salary: str = Form("0"), 
                            bonus_incentive: str = Form("250"), 
                            birthday: str = Form(""), 
                            start_date: str = Form(""),
                            status: str = Form("Activo"),
                            email: str = Form("")):
    try: base_salary_float = float(base_salary) if base_salary and base_salary.strip() else 0.0
    except: base_salary_float = 0.0
    try: bonus_incentive_float = float(bonus_incentive) if bonus_incentive and bonus_incentive.strip() else 0.0
    except: bonus_incentive_float = 0.0

    update_collaborator(
        collab_id, 
        role=role, 
        base_salary=base_salary_float, 
        bonus_incentive=bonus_incentive_float, 
        birthday=birthday, 
        start_date=start_date, 
        status=status, 
        email=email
    )
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@router.post("/hr/{collab_id}/upload_picture")
async def upload_hr_picture(collab_id: str, file: UploadFile = File(...)):
    collab = get_collaborator_details(collab_id)
    if collab and file.filename:
        # Save to Profile folder
        target_path = os.path.join(os.path.abspath("Collaborators"), collab.id, "Profile", file.filename)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as buffer:
            buffer.write(await file.read())
        update_collaborator_picture(collab_id, file.filename)
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@router.get("/hr_file/{collab_id}/{category}/{filename}")
async def get_hr_file(collab_id: str, category: str, filename: str):
    collab = get_collaborator_details(collab_id)
    if not collab: return HTMLResponse("Not Found", status_code=404)
    file_path = os.path.join(os.path.abspath("Collaborators"), collab.id, category, filename)
    if not os.path.exists(file_path): return HTMLResponse("File not found", status_code=404)
    return FileResponse(file_path)

@router.post("/hr/{collab_id}/upload")
async def upload_hr_file(collab_id: str, category: str = Form(...), file: UploadFile = File(...)):
    collab = get_collaborator_details(collab_id)
    if collab:
        target_path = os.path.join(os.path.abspath("Collaborators"), collab.id, category, file.filename)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@router.post("/hr/{collab_id}/adjustment/add")
async def create_adjustment(collab_id: str, type: str = Form(...), description: str = Form(...), amount: str = Form(...)):
    try: add_adjustment(collab_id, type, description, float(amount))
    except: pass
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@router.post("/hr/{collab_id}/adjustment/remove")
async def delete_adjustment(collab_id: str, adj_id: str = Form(...)):
    remove_adjustment(collab_id, adj_id)
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)

@router.post("/hr/{collab_id}/archive")
async def archive_collaborator_route(collab_id: str, archive: bool = Form(...)):
    toggle_archive_collaborator(collab_id, archive)
    return RedirectResponse("/hr", status_code=303)

@router.post("/hr/{collab_id}/payroll/close")
async def close_payroll_month(collab_id: str, month_year: str = Form(None)):
    try:
        collab = get_collaborator_details(collab_id)
        if not collab: return RedirectResponse(f"/hr", status_code=303)
        
        adjs = collab.adjustments if hasattr(collab, 'adjustments') and collab.adjustments else []
        total_bonos = sum(float(a['amount']) for a in adjs if a['type'] == 'Bono')
        total_descuentos = sum(float(a['amount']) for a in adjs if a['type'] == 'Descuento')
        
        isr_proj = calculate_isr_projection(collab.base_salary, collab.bonus_incentive)
        igss_laboral = collab.base_salary * 0.0483
        
        liquid = (collab.base_salary + collab.bonus_incentive + total_bonos) - (igss_laboral + isr_proj + total_descuentos)
        
        aguinaldo = collab.base_salary / 12
        bono14 = collab.base_salary / 12
        vacas = collab.base_salary / 24
        total_liability_month = aguinaldo + bono14 + vacas

        new_liability = getattr(collab, 'accumulated_liability', 0.0) + total_liability_month
        save_payroll_close(collab_id, new_liability)

    except Exception as e:
        print(f"Error closing payroll: {e}")
        
    return RedirectResponse(f"/hr/{collab_id}", status_code=303)


