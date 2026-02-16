"""Shared SQLAlchemy async engine + session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base."""
    pass


def create_db_engine(dsn: str, echo: bool = False):
    """Create async engine from DSN."""
    return create_async_engine(dsn, echo=echo, pool_pre_ping=True)


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
