from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from misra_platform.api.middleware import AuthMiddleware, CorrelationIdMiddleware, RateLimitMiddleware
from misra_platform.api.v1.observability import router as observability_router
from misra_platform.api.v1.router import api_v1_router
from misra_platform.core.config import get_settings
from misra_platform.core.logging import configure_logging, get_logger
from misra_platform.observability import PrometheusMiddleware, configure_tracing
from misra_platform.repositories.base import init_database

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    db = init_database(settings)
    logger.info(
        "application_started",
        environment=settings.environment.value,
        version=settings.version,
    )
    yield
    await db.dispose()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Enterprise MISRA C compliance platform API.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )
    app.add_middleware(AuthMiddleware, settings=settings)
    if settings.prometheus_enabled:
        app.add_middleware(PrometheusMiddleware)
    app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(CorrelationIdMiddleware)

    configure_tracing(app, settings)

    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    if settings.prometheus_enabled:
        app.include_router(observability_router)

    return app


app = create_app()
