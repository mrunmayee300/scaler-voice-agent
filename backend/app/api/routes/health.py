from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.rag.qdrant_store import health_check

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        qdrant=health_check(),
        environment=settings.environment,
    )
