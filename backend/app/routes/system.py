from fastapi import APIRouter

from app.dependencies import knowledge_base
from app.models import HealthResponse


router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", knowledge_base_loaded=len(knowledge_base.entries) > 0)


@router.post("/api/rebuild-index")
def rebuild_index() -> dict[str, str]:
    knowledge_base.rebuild_index()
    return {"status": "rebuilt"}
