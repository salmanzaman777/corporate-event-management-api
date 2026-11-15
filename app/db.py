"""Database engine, session factory, and declarative base.

Reads DATABASE_URL from the environment so no credentials are hardcoded.
All I/O in this project is async — the sync SQLAlchemy API is never used.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Read from env; fall back to a localhost default for local dev only.
# In production, always set DATABASE_URL explicitly.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/event_db",
)

# echo=False keeps logs clean; pool_pre_ping checks connections before reuse.
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# expire_on_commit=False keeps ORM objects usable after commit without re-fetching.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base — all ORM models inherit from this."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields one async session per request, rolls back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()  # undo any partial writes on unhandled error
            raise
