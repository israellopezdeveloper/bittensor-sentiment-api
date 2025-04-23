import asyncio
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from app.core.config import settings

"""
Async database session management using SQLModel and SQLAlchemy.
"""

DATABASE_URL: str = settings.database_url
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
)

async_session: Any = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session to be used in FastAPI dependencies.

    Yields:
        AsyncSession: A SQLModel-compatible async session.
    """
    async with async_session() as session:
        yield session


async def init_db(
    retries: int = settings.blockchain_max_retries,
    delay: int = settings.blockchain_retry_timeout,
) -> None:
    """
    Initialize the database by creating tables and retrying on connection failure.

    Args:
        retries (int): Number of retry attempts before giving up.
        delay (int): Delay (in seconds) between retries.

    Raises:
        RuntimeError: If connection fails after all retries.
    """
    for _ in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            return
        except Exception as _:
            await asyncio.sleep(delay)
    raise RuntimeError('[INIT] Could not connect to database after multiple attempts.')
