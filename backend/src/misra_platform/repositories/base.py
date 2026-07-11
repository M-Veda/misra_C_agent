from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from misra_platform.core.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: AsyncEngine = create_async_engine(
            str(settings.database_url),
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def dispose(self) -> None:
        await self.engine.dispose()


database: Database | None = None


def get_database() -> Database:
    if database is None:
        raise RuntimeError("Database has not been initialized")
    return database


def init_database(settings: Settings | None = None) -> Database:
    global database
    database = Database(settings or get_settings())
    return database


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    db = get_database()
    session = db.session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_scope() as session:
        yield session
