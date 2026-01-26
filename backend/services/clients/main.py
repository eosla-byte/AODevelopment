from fastapi import FastAPI
app = FastAPI(title="AO Clients")

@app.get("/health")
def health_check(): return {"status": "ok", "service": "AO Clients"}
