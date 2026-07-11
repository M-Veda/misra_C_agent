"""Prometheus metrics exposition for production observability."""

from __future__ import annotations

import time
from collections.abc import Callable

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

HTTP_REQUESTS_TOTAL = Counter(
    "misra_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "misra_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
ANALYSIS_RUNS_TOTAL = Counter(
    "misra_analysis_runs_total",
    "Total analysis runs started",
    ["status"],
)
VIOLATIONS_OPEN = Gauge(
    "misra_violations_open",
    "Current open violation count (updated on scrape via domain metrics)",
)
RULE_ENGINE_DURATION = Histogram(
    "misra_rule_engine_duration_seconds",
    "Rule engine execution duration per analysis run",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)


def record_analysis_run(*, status: str, duration_seconds: float) -> None:
    ANALYSIS_RUNS_TOTAL.labels(status=status).inc()
    RULE_ENGINE_DURATION.observe(duration_seconds)


def prometheus_metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        endpoint = request.url.path
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(response.status_code),
        ).inc()
        HTTP_REQUEST_DURATION.labels(method=request.method, endpoint=endpoint).observe(duration)
        return response
