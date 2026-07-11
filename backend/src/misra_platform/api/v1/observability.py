from fastapi import APIRouter
from fastapi.responses import Response

from misra_platform.observability.metrics import prometheus_metrics_response

router = APIRouter(tags=["Observability"], include_in_schema=False)


@router.get("/metrics")
async def get_prometheus_metrics() -> Response:
    return prometheus_metrics_response()
