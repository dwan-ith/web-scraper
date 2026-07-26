"""
Database Layer using SQLAlchemy (async)
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

engine = None
AsyncSessionLocal = None

async def init_db():
    global engine, AsyncSessionLocal
    try:
        db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(db_url, pool_size=10, echo=settings.debug)
        AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database connected")
    except Exception as e:
        logger.warning(f"Database unavailable ({e}). Running without DB.")

async def get_database():
    return AsyncSessionLocal
