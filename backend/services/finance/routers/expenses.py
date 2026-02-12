from fastapi import APIRouter, Request, Form, UploadFile, File, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
import shutil
import datetime
from typing import List
from common.database import (
    get_expenses_monthly, add_expense_column, add_expense_card,
    copy_expense_card, delete_expense_card, delete_expense_column,
    update_expense_card_files, get_projects, get_collaborators
)

router = APIRouter(
    tags=["Expenses"]
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

@router.get("/gastos", response_class=HTMLResponse)
async def read_gastos(request: Request, year: str = ""):
    current_year = datetime.datetime.now().year
    try: selected_year = int(year)
    except: selected_year = current_year
        
    expenses = get_expenses_monthly(selected_year)
    
    for col in expenses:
        col['total'] = sum(c['amount'] for c in col['cards'])
        
    grand_total = sum(col['total'] for col in expenses)
    available_years = [current_year - 1, current_year, current_year + 1]

    return templates.TemplateResponse("gastos.html", {
        "request": request,
        "expenses": expenses,
        "selected_year": selected_year,
        "available_years": available_years,
        "grand_total": grand_total
    })

@router.post("/gastos/column/add")
async def add_gastos_column(name: str = Form(...)):
    add_expense_column(name)
    return RedirectResponse("/gastos", status_code=303)

@router.post("/gastos/card/add")
async def add_gastos_card(
    column_id: str = Form(...),
    name: str = Form(...),
    amount: float = Form(...),
    description: str = Form(""),
    date: str = Form(None), 
    files: List[UploadFile] = File(None)
):
    card = add_expense_card(column_id, name, amount, description, [], date)
    if card and files:
        saved_filenames = []
        expense_dir = os.path.join(os.path.abspath("Expenses"), card['id'])
        os.makedirs(expense_dir, exist_ok=True)
        for file in files:
            if file.filename:
                file_path = os.path.join(expense_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                saved_filenames.append(file.filename)
        if saved_filenames:
            update_expense_card_files(card['id'], saved_filenames)
    return RedirectResponse("/gastos", status_code=303)

@router.post("/gastos/card/copy")
async def copy_gastos_card(card_id: str = Form(...), target_column_id: str = Form(...)):
    new_card_id = copy_expense_card(card_id, target_column_id)
    if new_card_id:
        src_dir = os.path.join(os.path.abspath("Expenses"), card_id)
        if os.path.exists(src_dir):
             dest_dir = os.path.join(os.path.abspath("Expenses"), new_card_id)
             try: shutil.copytree(src_dir, dest_dir)
             except: pass
    return RedirectResponse("/gastos", status_code=303)

@router.get("/gastos/file/{card_id}/{filename}")
async def get_gastos_file(card_id: str, filename: str):
    file_path = os.path.join(os.path.abspath("Expenses"), card_id, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTMLResponse("File not found", status_code=404)

# --- Socios (Partners) ---
@router.get("/socios", response_class=HTMLResponse)
async def read_socios(request: Request):
    projects = get_projects()
    collaborators = get_collaborators()
    partners = [c for c in collaborators if "socio" in c.role.lower()]
    
    partner_stats = {}
    for p in partners:
        partner_stats[p.id] = {
            "collab": p,
            "project_details": [],
            "total_balance": 0.0,
            "total_withdrawn": 0.0,
            "total_profit": 0.0
        }
    
    for proj in projects:
        shares = getattr(proj, 'partners_config', {}) or {}
        profit_pool = (proj.amount or 0.0) * ((proj.real_profit_margin or 0.0) / 100.0)
        
        for p_id in partner_stats.keys():
            share_pct = shares.get(p_id, 0.0)
            if share_pct > 0:
                partner_share_amount = profit_pool * (share_pct / 100.0)
                withdrawn = 0.0
                if proj.profit_withdrawals:
                     withdrawn = sum(w['amount'] for w in proj.profit_withdrawals if w['collab_id'] == p_id)
                
                balance = partner_share_amount - withdrawn
                partner_stats[p_id]["project_details"].append({
                    "project_name": proj.name,
                    "project_id": proj.id,
                    "share_pct": share_pct,
                    "total_profit_share": partner_share_amount,
                    "withdrawn": withdrawn,
                    "balance": balance,
                    "project_emoji": proj.emoji
                })
                partner_stats[p_id]["total_profit"] += partner_share_amount
                partner_stats[p_id]["total_withdrawn"] += withdrawn
                partner_stats[p_id]["total_balance"] += balance

    return templates.TemplateResponse("socios.html", {
        "request": request,
        "partners": partner_stats
    })
