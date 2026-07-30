from fastapi import APIRouter

from app.api.v1.complaint_drafts import router as complaint_drafts_router
from app.api.v1.health import router as health_router
from app.api.v1.reference import router as reference_router

router = APIRouter(prefix="/api/v1")
router.include_router(complaint_drafts_router)
router.include_router(health_router)
router.include_router(reference_router)
