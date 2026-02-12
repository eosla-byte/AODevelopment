from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import os
import sys
import datetime
from typing import Optional

# Path Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# from common.auth import create_access_token, decode_token
# from common.database import get_db

# Import Routers
# Using absolute imports based on sys.path hack
# from routers import projects, hr, expenses, quotes

app = FastAPI(title="AO Finance & Operations")

# CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static & Templates
# We rely on 'static' and 'templates' folders being present in service root.
# If they are missing, we might need to symlink or copy from monolith during build.
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Auth Middleware
# class AuthMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         return await call_next(request)

# app.add_middleware(AuthMiddleware)

# Include Routers
# app.include_router(projects.router)
# app.include_router(hr.router)
# app.include_router(expenses.router)
# app.include_router(quotes.router)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return HTMLResponse("<h1>Finance Service - Minimal Mode</h1><p>If you see this, deployment works.</p>")


@app.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("accounts_access_token")
    response.delete_cookie("access_token")
    return response

@app.get("/version_check")
def version_check():
    return {"service": "AO Finance", "version": "v2.0-migrated"}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "finance"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
