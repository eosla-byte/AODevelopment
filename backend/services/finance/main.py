from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os

from ...common.database import get_expenses_monthly, get_collaborators

app = FastAPI(title="AO HR & Finance")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/hr/list")
async def hr_list():
    return get_collaborators()

@app.get("/expenses/list")
async def expenses_list(year: int = None):
    return get_expenses_monthly(year)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AO HR & Finance"}
