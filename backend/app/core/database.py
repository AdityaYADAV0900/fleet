import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.normalized_database_url
        connect_args = {}
        if "asyncpg" in db_url:
            connect_args["statement_cache_size"] = 0
            if "localhost" not in db_url and "127.0.0.1" not in db_url:
                connect_args["ssl"] = "require"

        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            poolclass=pool.NullPool,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database_connection() -> dict[str, Any]:
    """Check connectivity to PostgreSQL by executing a ping query."""
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            if val == 1:
                return {"status": "connected", "error": None}
            return {"status": "error", "error": f"Unexpected ping result: {val}"}
    except Exception as exc:
        logger.warning(f"Database connection check failed: {exc}")
        return {"status": "disconnected", "error": str(exc)}
