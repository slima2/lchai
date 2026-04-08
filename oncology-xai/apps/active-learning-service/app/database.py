"""Database session management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

async_engine = create_async_engine(settings.postgres_dsn, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

sync_engine = create_engine(settings.postgres_dsn_sync, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(sync_engine, class_=Session)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def get_sync_db() -> Session:
    return SyncSessionLocal()
