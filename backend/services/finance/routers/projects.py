from fastapi import APIRouter

router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"]
)

@router.get("/")
def list_projects():
    return [{"id": "1", "name": "Project Alpha", "status": "In Progress"}]
