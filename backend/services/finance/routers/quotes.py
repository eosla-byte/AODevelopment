from fastapi import APIRouter

router = APIRouter(
    prefix="/api/quotes",
    tags=["Quotes"]
)

@router.get("/")
def list_quotes():
    return [{"id": "1", "client": "Client X", "total": 50000.00}]
