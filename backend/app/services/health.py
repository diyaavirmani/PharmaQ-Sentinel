from app.core.config import get_settings
from app.core.database import check_database_connection
from app.schemas.health import DatabaseHealth, HealthResponse


def build_health_response() -> HealthResponse:
    settings = get_settings()
    database_connected = check_database_connection()

    return HealthResponse(
        status="healthy" if database_connected else "degraded",
        service=settings.service_name,
        version=settings.app_version,
        database=DatabaseHealth(
            provider="mysql",
            status="connected" if database_connected else "unavailable",
        ),
    )
