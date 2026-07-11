from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.config import Settings, get_settings
from misra_platform.integrations.clang_bridge.ast_client import ClangAstClient
from misra_platform.integrations.redis.cache import RedisClientFactory
from misra_platform.repositories.base import get_db_session


async def get_settings_dependency() -> Settings:
    return get_settings()


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_redis_client(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> AsyncGenerator[Redis, None]:
    client = RedisClientFactory.create(settings)
    try:
        yield client
    finally:
        await client.aclose()


async def get_clang_client(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ClangAstClient:
    return ClangAstClient(settings)


def get_correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")
