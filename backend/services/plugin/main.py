from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Ensure backend root is in path or rely on being run from root
# We import routers from the shared 'routers' directory for now
# (Refactoring to move them inside services/plugin is Phase 2)
# from .routers import plugin_api, plugin_cloud, ai, sheet_api

# Unified Auth
try:
    from common.auth import require_service
except ImportError:
    # Adjust path if running locally inside service folder
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from common.auth import require_service

from fastapi import Depends
from .routers import plugin_api, plugin_cloud, sheet_api

app = FastAPI(title="AOdev (Plugin Service)")

# CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://daily.somosao.com",
    "https://accounts.somosao.com",
    "https://bim.somosao.com",
    "https://aodev.railway.internal",
    "https://somosao.com",
    "https://www.somosao.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
# plugin_api handles its own mixed auth (login vs protected)
app.include_router(plugin_api.router) 
app.include_router(plugin_cloud.router, dependencies=[Depends(require_service("plugin"))])
# app.include_router(ai.router, dependencies=[Depends(require_service("plugin"))])
app.include_router(sheet_api.router, dependencies=[Depends(require_service("plugin"))])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AOdev", "version": "1.0.0"}

