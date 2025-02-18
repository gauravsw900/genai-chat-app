from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.memory_service import memory_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    redis_ok = await memory_service.health_check()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "redis": "connected" if redis_ok else "disconnected",
            "openai": "configured",
            "rag": "ready",
            "agent": "ready"
        }
    )
