"""
Database connection management with async SQLAlchemy.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import get_settings

# Global engine and session factory
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global _engine

    if _engine is None:
        settings = get_settings()

        # Use NullPool for async to avoid connection issues
        # In production, you may want to configure pool settings
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,  # Verify connections before use
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory."""
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    return _session_factory


async def init_db() -> None:
    """
    Initialize the database.

    This creates all tables if they don't exist.
    In production, use Alembic migrations instead.
    """
    from src.db.models import Base

    engine = get_engine()
    async with engine.begin() as conn:
        # Create pgvector extension if not exists
        await conn.execute(
            "CREATE EXTENSION IF NOT EXISTS vector"  # type: ignore
        )
        # Create tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close the database connection."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as an async context manager.

    Usage:
        async with get_db() as db:
            result = await db.execute(query)
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session for FastAPI dependency injection.

    Usage:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with get_db() as session:
        yield session
