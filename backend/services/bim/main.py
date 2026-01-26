from fastapi import FastAPI
app = FastAPI(title="AOplanSystem (BIM)")

@app.get("/health")
def health_check(): return {"status": "ok", "service": "AOplanSystem"}
