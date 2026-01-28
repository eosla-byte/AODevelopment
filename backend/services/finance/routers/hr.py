from fastapi import APIRouter

router = APIRouter(
    prefix="/api/hr",
    tags=["HR"]
)

@router.get("/employees")
def list_employees():
    return [{"id": "1", "name": "John Doe", "role": "Architect"}]
