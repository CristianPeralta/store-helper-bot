"""Pytest configuration and fixtures."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock
from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine

# Create a simple in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=True
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for our test tables
Base = declarative_base()

# Fixtures para la sesión de base de datos
@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    
    # Configurar el comportamiento de commit y rollback
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    
    return session

# Modelo de prueba para BaseService
class TestModel(Base):
    __tablename__ = 'test_model'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    value = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# Fixture para el modelo base
@pytest.fixture
def base_model():
    """Create a mock model for testing BaseService."""
    return TestModel

# Fixture para el servicio base
@pytest.fixture
def base_service(base_model):
    """Create a BaseService instance for testing."""
    from app.services import BaseService
    return BaseService(base_model)

# Fixture para un objeto de base de datos de prueba
@pytest.fixture
def test_db_object():
    """Create a test database object."""
    return TestModel(id=1, name="Test Item", description="Test Description", value=42)
