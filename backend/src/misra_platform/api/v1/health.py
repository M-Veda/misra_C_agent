from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.config import Settings
from misra_platform.core.dependencies import (
    get_clang_client,
    get_database_session,
    get_redis_client,
    get_settings_dependency,
)
from misra_platform.integrations.clang_bridge.ast_client import ClangAstClient

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    version: str
    environment: str
    timestamp: datetime


class DependencyCheck(BaseModel):
    status: Literal["up", "down"]
    latency_ms: float
    message: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded"]
    checks: dict[str, DependencyCheck] = Field(default_factory=dict)


@router.get("/health", response_model=HealthResponse)
async def get_health(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> HealthResponse:
    return HealthResponse(
        version=settings.version,
        environment=settings.environment.value,
        timestamp=datetime.now(UTC),
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def get_readiness(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    clang_client: Annotated[ClangAstClient, Depends(get_clang_client)],
) -> JSONResponse | ReadinessResponse:
    import time

    checks: dict[str, DependencyCheck] = {}

    db_started = time.perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = DependencyCheck(
            status="up",
            latency_ms=round((time.perf_counter() - db_started) * 1000, 2),
        )
    except Exception as error:
        checks["database"] = DependencyCheck(
            status="down",
            latency_ms=round((time.perf_counter() - db_started) * 1000, 2),
            message=str(error),
        )

    redis_started = time.perf_counter()
    try:
        pong = await redis.ping()
        checks["redis"] = DependencyCheck(
            status="up" if pong else "down",
            latency_ms=round((time.perf_counter() - redis_started) * 1000, 2),
            message="PONG" if pong else "No response",
        )
    except Exception as error:
        checks["redis"] = DependencyCheck(
            status="down",
            latency_ms=round((time.perf_counter() - redis_started) * 1000, 2),
            message=str(error),
        )

    clang_health = await clang_client.check_health()
    checks["clang_worker"] = DependencyCheck(
        status="up" if clang_health["status"] == "up" else "down",
        latency_ms=float(clang_health["latency_ms"]),
        message=str(clang_health.get("message")),
    )

    all_up = all(check.status == "up" for check in checks.values())
    response = ReadinessResponse(
        status="ready" if all_up else "degraded",
        checks=checks,
    )

    if all_up:
        return response

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(mode="json"),
    )
