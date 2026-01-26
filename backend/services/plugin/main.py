from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Ensure backend root is in path or rely on being run from root
# We import routers from the shared 'routers' directory for now
# (Refactoring to move them inside services/plugin is Phase 2)
from ...routers import plugin_api, plugin_cloud, ai, sheet_api

app = FastAPI(title="AOdev (Plugin Service)")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(plugin_api.router)
app.include_router(plugin_cloud.router)
app.include_router(ai.router)
app.include_router(sheet_api.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AOdev", "version": "1.0.0"}
