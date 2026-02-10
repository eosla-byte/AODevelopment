from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import os
import sys

# Path Setup for local common module
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from .routers import projects, hr, expenses, quotes

app = FastAPI(title="AO Finance & Operations")

# Mount Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

from .common.auth import require_service
from fastapi import Depends

# Include Routers with Auth & Entitlement Check
app.include_router(projects.router, dependencies=[Depends(require_service("finance"))])
app.include_router(hr.router, dependencies=[Depends(require_service("finance"))])
app.include_router(expenses.router, dependencies=[Depends(require_service("finance"))])
app.include_router(quotes.router, dependencies=[Depends(require_service("finance"))])

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "AO Admin"})

@app.get("/version_check")
def version_check():
    return {"service": "AO Finance", "version": "v1.0"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
