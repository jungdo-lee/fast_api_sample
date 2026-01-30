import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_db.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_JSON"] = "false"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["JWT_PRIVATE_KEY_PATH"] = "keys/private.pem"
os.environ["JWT_PUBLIC_KEY_PATH"] = "keys/public.pem"

# Import models AFTER setting env vars so config picks them up
from app.models import Base, LoginHistory, User, UserDevice  # noqa: E402, F401
from app.dependencies.database import get_db  # noqa: E402
from app.dependencies.redis import get_redis  # noqa: E402

test_engine = create_async_engine("sqlite+aiosqlite:///./test_db.db", echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def mock_redis() -> AsyncMock:
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.sadd = AsyncMock()
    redis_mock.srem = AsyncMock()
    redis_mock.smembers = AsyncMock(return_value=set())
    return redis_mock


@pytest_asyncio.fixture
async def client(mock_redis: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    from app.core.rate_limit import limiter
    from app.main import create_app

    limiter.enabled = False
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_redis():
        yield mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
