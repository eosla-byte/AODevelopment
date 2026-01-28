from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import os
import datetime

app = FastAPI(title="AO Build")

@app.get("/")
def health_check():
    return {"service": "AO Build", "status": "running", "timestamp": datetime.datetime.now().isoformat()}

@app.get("/version_check")
def version_check():
    return {"version": "v1_build_init"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8006)) # Different port than others just incase local
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
