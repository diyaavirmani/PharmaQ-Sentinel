from typing import Literal

from pydantic import BaseModel


class DatabaseHealth(BaseModel):
    provider: Literal["mysql"]
    status: Literal["connected", "unavailable"]


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: Literal["pharmaq-sentinel-api"]
    version: str
    database: DatabaseHealth
