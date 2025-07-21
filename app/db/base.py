from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.config import get_settings

settings = get_settings()

class Database:
    """Database configuration and session management."""
    
    def __init__(self, url: Optional[str] = None):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._url = url or settings.DATABASE_URL
    
    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                self._url,
                echo=settings.DEBUG,
                future=True,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=20,
                max_overflow=10,
            )
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False
            )
        return self._session_factory
    
    async def create_all(self):
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_all(self):
        """Drop all database tables (use with caution)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def close(self):
        """Close the database connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

# Create a single instance
database = Database()

# Base class for all models
Base = declarative_base()
