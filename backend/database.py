"""Database setup: engine, session, and base model."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator

import os
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


is_testing = bool(os.environ.get("RUN_DB_TESTS") or os.environ.get("TESTING"))

engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    poolclass=NullPool if is_testing else None,
    pool_pre_ping=True if not is_testing else False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# Synchronous engine and session for tests
sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
sync_engine = create_engine(sync_database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
sync_session_factory = sessionmaker(sync_engine, class_=Session, expire_on_commit=False, autoflush=False)


def get_sync_session() -> Generator[Session, None, None]:
    """Synchronous database session for tests."""
    db = sync_session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of FastAPI."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. For development only - use Alembic in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database engine."""
    await engine.dispose()