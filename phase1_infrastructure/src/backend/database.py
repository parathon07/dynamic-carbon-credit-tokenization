"""
Database Connection Manager
============================
Provides sync and async SQLAlchemy engines + session factories
for the PostgreSQL/TimescaleDB backend.
"""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import ASYNC_DATABASE_URL, DATABASE_URL

# ── Synchronous engine (for migrations / CLI tools) ──────────────────────
sync_engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)
SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session)


@contextmanager
def get_sync_session():
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Asynchronous engine (for FastAPI request handlers) ───────────────────
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=False,
)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncSession:
    """FastAPI dependency for DB sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
