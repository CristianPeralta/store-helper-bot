"""Pytest configuration and fixtures."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import sys
from typing import AsyncGenerator, AsyncIterator, Generator
from unittest.mock import AsyncMock

# Import the get_db function
from app.db.session import get_db

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

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
    connection = await engine.connect()
    
    # Begin a non-ORM transaction
    transaction = await connection.begin()
    
    # Create a session with the connection
    TestingSessionLocal = sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )
    
    # Create the session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        # Clean up
        await session.close()
        await transaction.rollback()
        await connection.close()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db(engine, db_session):
    """Set up the database before each test and clean up after."""
    # Drop all tables and recreate them
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Ensure the session is committed and closed after setup
    await db_session.commit()
    await db_session.close()

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
    from app.services import BaseService
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
def test_message(test_chat, db_session):
    """Create a test message instance."""
    message = Message(
        chat_id=test_chat.id,
        content="Test message",
        sender=Sender.CLIENT,
        intent=MessageIntent.GREETING
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message

# Create a test FastAPI app
@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI application."""
    from app.main import app as fastapi_app
    return fastapi_app

# Create a test client
@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def ensure_cleanup():
    """Ensure all connections are properly closed after tests complete."""
    yield  # Run all tests first
    
    # Clean up any remaining resources
    import asyncio
    import gc
    
    # Get the current event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run any pending tasks
    pending = asyncio.all_tasks(loop=loop)
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    
    # Force garbage collection to clean up any remaining resources
    gc.collect()
    
    # Close the event loop
    if loop.is_running():
        loop.stop()
    if not loop.is_closed():
        loop.close()

# Create an async test client
@pytest_asyncio.fixture
async def async_client(app: FastAPI, db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application.
    
    Ensures proper cleanup of AsyncClient and its underlying connections.
    """
    async def get_test_db():
        try:
            yield db_session
        finally:
            # Don't close the session here, let the fixture handle it
            pass
    
    # Override the database dependency
    app.dependency_overrides[get_db] = get_test_db
    
    # Configure AsyncClient with explicit timeout and connection limits
    transport = None
    try:
        transport = AsyncClient(
            app=app,
            base_url="http://test",
            timeout=30.0,  # Add a reasonable timeout
            follow_redirects=True,  # Enable redirect following
            http2=False,  # Disable HTTP/2 to avoid potential connection issues
        )
        yield transport
    finally:
        # Ensure proper cleanup of the transport
        if transport is not None:
            await transport.aclose()
        
        # Clear overrides
        app.dependency_overrides.clear()
        
        # Force garbage collection to ensure connections are closed
        import gc
        gc.collect()
