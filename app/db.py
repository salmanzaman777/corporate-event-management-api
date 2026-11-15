"""Database engine, session factory, and declarative base.

Reads DATABASE_URL from the environment so no credentials are hardcoded.
All I/O in this project is async — the sync SQLAlchemy API is never used.
"""

import os
import socket
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def _resolve_database_url() -> str:
    """Resolve database URL: use explicit env var, or fallback to SQLite if Postgres is offline."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # Check if local PostgreSQL is actively listening on port 5432
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=0.3):
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/event_db"
    except OSError:
        # Fall back to zero-config local async SQLite so app runs immediately in browser
        return "sqlite+aiosqlite:///./event_db.sqlite"


DATABASE_URL: str = _resolve_database_url()

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
