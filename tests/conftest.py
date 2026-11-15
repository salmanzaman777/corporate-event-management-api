"""pytest configuration and shared fixtures.

Uses an in-memory SQLite database (via aiosqlite) so no PostgreSQL is needed
for the test suite. Each test gets a fresh database to avoid state leakage.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base, get_db
from app.main import app

# SQLite async URL — no external service required for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a fresh async SQLite engine and all tables for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    """Async HTTPX client wired to the FastAPI app with the test database."""
    test_session_factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: register a user and return an auth token
# ---------------------------------------------------------------------------

async def get_auth_token(client: AsyncClient, username: str = "testuser") -> str:
    """Register a user and return a bearer token for use in test headers."""
    await client.post("/auth/register", json={
        "username": username,
        "email": f"{username}@test.com",
        "password": "TestPass123",
    })
    resp = await client.post("/auth/login", json={
        "username": username,
        "password": "TestPass123",
    })
    return resp.json()["access_token"]
