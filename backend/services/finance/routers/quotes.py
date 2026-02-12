from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
import uuid
from typing import Optional
from common.database import (
    get_quotations, get_quotation_by_id, create_quotation, update_quotation, delete_quotation,
    get_templates, save_template, get_projects, get_market_studies
)

router = APIRouter(
    tags=["Quotes"]
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

@router.get("/cotizaciones", response_class=HTMLResponse)
async def view_quotations(request: Request):
    quotations = get_quotations()
    return templates.TemplateResponse("cotizaciones_list.html", {
        "request": request,
        "quotations": quotations
    })

@router.get("/cotizaciones/new")
async def new_quotation(request: Request, template_id: Optional[str] = None, blank: Optional[str] = None):
    # Select Template Screen
    if not template_id and not blank:
         tpls = get_templates()
         list_items = [f'<a href="/cotizaciones/new?template_id={t.id}" class="flex items-center gap-3 p-4 border border-slate-200 rounded-xl hover:bg-indigo-50 border-transparent hover:border-indigo-200 transition-all group decoration-0 cursor-pointer"><span class="text-2xl">📑</span><div><div class="font-bold text-indigo-900">{t.name}</div><div class="text-xs text-indigo-400">Plantilla personalizada</div></div></a>' for t in tpls]
         
         full_html = f"""
        <html><head><script src="https://cdn.tailwindcss.com"></script><link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;700;900&display=swap" rel="stylesheet"><style>body{{font-family:'Barlow',sans-serif}} a{{text-decoration:none!important}}</style></head>
        <body class="bg-slate-100 flex items-center justify-center h-screen">
            <div class="bg-white p-8 rounded-xl shadow-xl max-w-lg w-full text-center">
                <h1 class="text-3xl font-black mb-6 text-slate-800">Nueva Cotización</h1>
                <p class="mb-6 text-slate-500">Selecciona una plantilla para comenzar:</p>
                <div class="space-y-3 mb-8 text-left max-h-[60vh] overflow-y-auto custom-scrollbar px-1">
                    <a href="/cotizaciones/new?blank=1" class="flex items-center gap-3 p-4 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors group">
                        <span class="text-2xl group-hover:scale-110 transition-transform">📄</span>
                        <div>
                            <div class="font-bold text-slate-800">Estándar (En Blanco)</div>
                            <div class="text-xs text-slate-400">Estructura básica de 5 páginas</div>
                        </div>
                    </a>
                    { "".join(list_items) }
                </div>
                <a href="/cotizaciones" class="text-slate-400 hover:text-slate-600 text-sm font-bold uppercase tracking-wider">Cancelar</a>
            </div>
        </body></html>
        """
         return HTMLResponse(full_html)

    new_id = str(uuid.uuid4())
    initial_blocks = []
    
    if template_id:
        tpls = get_templates()
        tgt = next((t for t in tpls if str(t.id) == str(template_id)), None)
        if tgt: initial_blocks = tgt.content_json

    if not initial_blocks:
        initial_blocks = [
            { "type": "page_config", "content": { "isCover": True, "backgroundImage": "/static/img/cover_bg.png" } },
            { "type": "page_break", "content": "" },
            { "type": "page_config", "content": { "isCover": True, "backgroundImage": "/static/img/page2_fixed.png" } },
            { "type": "page_break", "content": "" },
            { "type": "text", "content": "<h3 class='font-bold text-lg text-indigo-700 mb-2'>ALCANCE DE SERVICIOS</h3><p>Detalle de las etapas y entregables propuestos:</p>" },
            { "type": "page_break", "content": "" },
            { "type": "text", "content": "<h3 class='font-bold text-slate-800 mb-4 text-xl'>TÉRMINOS Y CONDICIONES</h3><ul class='list-disc pl-5 space-y-2 text-sm'><li>La presente oferta tiene una validez de 15 días.</li><li>Los pagos se realizarán según avance de entregables.</li><li>Cualquier cambio sustancial en el alcance requerirá una reestimación de honorarios.</li></ul>" },
            { "type": "page_break", "content": "" },
            { "type": "page_config", "content": { "isCover": True, "backgroundImage": "/static/img/back_bg.png" } }
        ]

    data = {
        "id": new_id,
        "title": "Nueva Cotización",
        "client_name": "",
        "status": "Borrador",
        "content_json": initial_blocks,
        "total_amount": 0.0
    }
    create_quotation(data)
    return RedirectResponse(f"/cotizaciones/{new_id}/edit", status_code=303)

@router.get("/cotizaciones/{id}/edit", response_class=HTMLResponse)
async def edit_quotation(request: Request, id: str):
    quotation = get_quotation_by_id(id)
    if not quotation:
        return RedirectResponse("/cotizaciones")
    return templates.TemplateResponse("cotizacion_editor.html", {
        "request": request,
        "quotation": quotation
    })

@router.post("/cotizaciones/update")
async def update_quotation_route(request: Request):
    try:
        data = await request.json()
        quot_id = data.get('id')
        updates = data.get('updates', {})
        updated_q = update_quotation(quot_id, updates)
        if updated_q: return JSONResponse({"status": "success"})
        else: return JSONResponse({"status": "error", "message": "Quotation not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@router.post("/cotizaciones/delete")
async def delete_quotation_route(request: Request):
    form = await request.form()
    quot_id = form.get('quot_id')
    delete_quotation(quot_id)
    return RedirectResponse("/cotizaciones", status_code=303)

@router.post("/cotizaciones/templates")
async def save_template_route(request: Request):
    try:
        data = await request.json()
        name = data.get("name")
        content = data.get("content_json")
        if not name or not content: return JSONResponse({"status": "error", "message": "Missing name or content"}, status_code=400)
        tpl = save_template(name, content)
        if tpl: return JSONResponse({"status": "success", "id": tpl})
        else: return JSONResponse({"status": "error", "message": "DB Error"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
