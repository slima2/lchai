"""Database setup for ontology-admin-service."""

from oncology_common.database import Base, create_db_engine, create_session_factory
from app.config import settings

engine = create_db_engine(settings.postgres_dsn)
async_session = create_session_factory(engine)


async def get_db():
    async with async_session() as session:
        yield session
