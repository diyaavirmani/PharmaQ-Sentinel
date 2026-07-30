from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health import build_health_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return build_health_response()
