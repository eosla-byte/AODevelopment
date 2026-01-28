from fastapi import APIRouter

router = APIRouter(
    prefix="/api/expenses",
    tags=["Expenses"]
)

@router.get("/")
def list_expenses():
    return [{"id": "1", "amount": 1500.00, "category": "Materials"}]
