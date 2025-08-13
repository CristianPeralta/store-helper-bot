"""Pytest configuration and fixtures."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import sys
from typing import AsyncGenerator, AsyncIterator, Generator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import Column, DateTime, Integer, String, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import the database configuration
from app.db.base import Base, database
from app.db.models.chat import Chat, Intent as ChatIntent
from app.db.models.message import Message, Sender, Intent as MessageIntent

# Override the database URL for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create a test engine with a shared connection
async def create_test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=True,
        future=True,
        connect_args={"check_same_thread": False}
    )
    return engine

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create and configure the test database engine."""
    engine = await create_test_engine()
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(engine):
    """
    Create a fresh database session for each test.
    Uses a connection that's closed after the test.
    """
    # Create a session factory
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )
    
    # Create a new session
    session = async_session()
    
    # Begin a transaction that will be rolled back after the test
    transaction = await session.begin()
    
    try:
        yield session
    finally:
        # Always roll back the transaction to clean up
        await transaction.rollback()
        await session.close()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db(engine):
    """Set up the database before each test and clean up after."""
    # Drop all tables before each test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest.fixture
def session_factory(engine):
    """Create a session factory for tests."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )

# Override the database engine and session factory for the application
@pytest.fixture(autouse=True)
async def override_database(engine):
    """Override the database engine and session factory for tests."""
    original_engine = database._engine
    original_session_factory = database._session_factory
    
    # Create a new session factory with the test engine
    test_session_factory = sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    database._engine = engine
    database._session_factory = test_session_factory
    
    yield
    
    # Restore the original engine and session factory
    database._engine = original_engine
    database._session_factory = original_session_factory

# Fixture for mocking database session
@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    
    # Configure commit and rollback behavior
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    
    return session

# Test model for BaseService
class TestModel(Base):
    """Test model for testing purposes."""
    __tablename__ = 'test_model'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    value = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# Fixture for the base model
@pytest.fixture
def base_model():
    """Create a mock model for testing BaseService."""
    return TestModel

# Fixture for the base service
@pytest.fixture
def base_service(base_model):
    """Create a BaseService instance for testing."""
    from app.services.base import BaseService
    return BaseService(base_model)

# Fixture for a test database object
@pytest.fixture
def test_db_object():
    """Create a test database object."""
    return TestModel(
        id=1, 
        name="Test Item", 
        description="Test Description", 
        value=42
    )

# Fixture for creating a test chat
@pytest.fixture
async def test_chat(db_session):
    """Create a test chat instance."""
    chat = Chat(
        client_name="Test User",
        client_email="test@example.com",
        initial_intent=ChatIntent.GENERAL_QUESTION
    )
    db_session.add(chat)
    await db_session.commit()
    return chat

# Fixture for creating a test message
@pytest.fixture
async def test_message(test_chat, db_session):
    """Create a test message instance."""
    message = Message(
        chat_id=test_chat.id,
        content="Test message",
        sender=Sender.CLIENT,
        intent=MessageIntent.GENERAL_QUESTION
    )
    db_session.add(message)
    await db_session.commit()
    return message
