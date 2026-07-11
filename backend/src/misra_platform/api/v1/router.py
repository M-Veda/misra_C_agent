from fastapi import APIRouter

from misra_platform.api.v1.analysis import router as analysis_router
from misra_platform.api.v1.bulk_review import router as bulk_review_router
from misra_platform.api.v1.cfg import router as cfg_router
from misra_platform.api.v1.health import router as health_router
from misra_platform.api.v1.compliance import router as compliance_router
from misra_platform.api.v1.exports import router as exports_router
from misra_platform.api.v1.integrations import router as integrations_router
from misra_platform.api.v1.metrics import router as metrics_router
from misra_platform.api.v1.reviews import router as reviews_router
from misra_platform.api.v1.rules import router as rules_router
from misra_platform.api.v1.teams import router as teams_router
from misra_platform.api.v1.violations import router as violations_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(analysis_router)
api_v1_router.include_router(cfg_router)
api_v1_router.include_router(rules_router)
api_v1_router.include_router(violations_router)
api_v1_router.include_router(reviews_router)
api_v1_router.include_router(bulk_review_router)
api_v1_router.include_router(metrics_router)
api_v1_router.include_router(exports_router)
api_v1_router.include_router(integrations_router)
api_v1_router.include_router(teams_router)
api_v1_router.include_router(compliance_router)
