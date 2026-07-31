from fastapi import APIRouter

from app.agents.complaint.router import router as complaint_agent_router
from app.api.v1.ai import router as ai_router
from app.api.v1.complaint_drafts import router as complaint_drafts_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.health import router as health_router
from app.api.v1.reference import router as reference_router

router = APIRouter(prefix="/api/v1")
router.include_router(ai_router)
router.include_router(complaint_agent_router)
router.include_router(complaint_drafts_router)
router.include_router(complaints_router)
router.include_router(evidence_router)
router.include_router(health_router)
router.include_router(reference_router)
