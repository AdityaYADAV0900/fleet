import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

TEST_DB_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or os.environ.get("DATABASE_URL_TEST")
    or settings.effective_test_database_url
)


@pytest.fixture(scope="session")
def test_db_url() -> str:
    return TEST_DB_URL


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an isolated AsyncSession using NullPool to prevent event-loop-closed errors."""
    engine = create_async_engine(
        TEST_DB_URL,
        poolclass=pool.NullPool,
        echo=False,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        try:
            await session.rollback()
        except Exception:
            pass
    await engine.dispose()
