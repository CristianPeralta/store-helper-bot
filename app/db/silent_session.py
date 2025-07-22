"""
Silent database session factory that suppresses all SQLAlchemy logging.
"""
import os
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

# Disable all SQLAlchemy logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
os.environ['SQLALCHEMY_SILENCE_UBER_WARNING'] = '1'

# Get database URL from settings
settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

# Create engine with echo=False to disable logging
engine = create_async_engine(DATABASE_URL, echo=False)

# Create session factory
async_session_factory = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

@asynccontextmanager
async def get_db_session():
    """Create a new async database session with logging disabled."""
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
