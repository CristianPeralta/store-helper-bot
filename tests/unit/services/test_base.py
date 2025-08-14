"""Tests for the BaseService class."""
from typing import List, Any, Type, Dict, Optional, Union, Generic, TypeVar
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

# Import the BaseService class
from app.services import BaseService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base

# Create a new base for our test models to avoid conflicts
ModelBase = declarative_base()

# Create a test model specifically for these tests
class _MockDataModel(ModelBase):
    """Mock model for BaseService tests.
    
    Note: Starts with underscore to prevent pytest from collecting it as a test class.
    """
    __test__ = False  # Tell pytest explicitly not to collect this as a test class
    __tablename__ = 'mock_data_model'  # Unique table name to avoid conflicts
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    value = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<_MockDataModel(id={self.id}, name='{self.name}')>"

# Mock schemas for testing
class MockCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    value: int = 0

class MockUpdateSchema(MockCreateSchema):
    pass

# Alias for backward compatibility in tests
TestModel = _MockDataModel

# Add the project root to the Python path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))  # Adjust to reach project root

# Now import the service
from app.services import BaseService

@pytest.mark.asyncio
class TestBaseService:
    """Test cases for BaseService."""
    
    async def test_get_existing_item(
        self, 
        base_service: Any, 
        mock_db_session: AsyncMock, 
        test_db_object: Any
    ) -> None:
        """Test getting an existing item by ID returns the correct item."""
        # Arrange
        item_id = 1
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = test_db_object
        mock_db_session.execute.return_value = mock_result
        
        # Act
        result = await base_service.get(mock_db_session, id=item_id)
        
        # Assert
        assert result == test_db_object
        mock_db_session.execute.assert_called_once()
        
        # Verify the query includes the correct WHERE clause
        args, _ = mock_db_session.execute.call_args
        query = args[0]
        assert hasattr(query, 'whereclause')
        assert 'id = :id_1' in str(query)
        
    async def test_get_nonexistent_item(
        self, 
        base_service: Any, 
        mock_db_session: AsyncMock
    ) -> None:
        """Test getting a non-existent item returns None."""
        # Arrange
        non_existent_id = 999
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Act
        result = await base_service.get(mock_db_session, id=non_existent_id)
        
        # Assert
        assert result is None
        mock_db_session.execute.assert_called_once()
        
    async def test_create_item(
        self, 
        base_service: Any, 
        mock_db_session: AsyncMock
    ) -> None:
        """Test creating a new item with valid data."""
        # Arrange
        item_data = MockCreateSchema(
            name="Test Item", 
            description="Test Description", 
            value=42
        )
        
        # Act
        result = await base_service.create(mock_db_session, obj_in=item_data)
        
        # Assert
        assert result is not None
        assert result.name == item_data.name
        assert result.description == item_data.description
        assert result.value == item_data.value
        
        # Verify database interactions
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once()
        
        # Verify the added object matches the input data
        added_obj = mock_db_session.add.call_args[0][0]
        assert added_obj.name == item_data.name
        assert added_obj.description == item_data.description
        assert added_obj.value == item_data.value
        
    async def test_update_item(
        self, 
        base_service: Any, 
        mock_db_session: AsyncMock, 
        test_db_object: Any
    ) -> None:
        """Test updating an existing item with valid data."""
        # Arrange
        original_name = test_db_object.name
        original_value = test_db_object.value
        update_data = MockUpdateSchema(name="Updated Name", value=100)
        
        # Act
        result = await base_service.update(
            mock_db_session,
            db_obj=test_db_object,
            obj_in=update_data
        )
        
        # Assert
        assert result == test_db_object
        assert test_db_object.name == "Updated Name"
        assert test_db_object.name != original_name  # Verify name changed
        assert test_db_object.value == 100
        assert test_db_object.value != original_value  # Verify value changed
        
        # Verify database interactions
        mock_db_session.add.assert_called_once_with(test_db_object)
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(test_db_object)
        
    async def test_remove_item(
        self, 
        base_service: Any, 
        mock_db_session: AsyncMock, 
        test_db_object: Any
    ) -> None:
        """Test removing an existing item."""
        # Arrange
        item_id = 1
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = test_db_object
        mock_db_session.execute.return_value = mock_result
        
        # Act
        result = await base_service.remove(mock_db_session, id=item_id)
        
        # Assert
        assert result == test_db_object
        mock_db_session.delete.assert_called_once_with(test_db_object)
        mock_db_session.commit.assert_awaited_once()
        
        # Verify the correct item was requested for deletion
        args, _ = mock_db_session.execute.call_args
        query = args[0]
        assert 'id = :id_1' in str(query)
        
    async def test_remove_nonexistent_item(
        self, 
        base_service: Any, 
        mock_db_session: AsyncMock
    ) -> None:
        """Test removing a non-existent item returns None."""
        # Arrange
        non_existent_id = 999
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Act
        result = await base_service.remove(mock_db_session, id=non_existent_id)
        
        # Assert
        assert result is None
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()
        
        # Verify the query was made for the correct ID
        args, _ = mock_db_session.execute.call_args
        query = args[0]
        assert 'id = :id_1' in str(query)
        
    async def test_get_multi(
        self, 
        base_service: BaseService[TestModel, MockCreateSchema, MockUpdateSchema],
        mock_db_session: AsyncMock,
        test_db_object: TestModel
    ) -> None:
        """Test retrieving multiple items with pagination."""
        # Arrange
        skip = 0
        limit = 10
        expected_items = [test_db_object]
        
        # Create a mock result with the expected structure
        mock_result = MagicMock()
        
        # Set up the mock chain:
        # 1. session.execute() returns a coroutine that resolves to mock_result
        # 2. mock_result.scalars() returns a mock
        # 3. .all() returns a coroutine that resolves to expected_items
        mock_db_session.execute.return_value = mock_result
        mock_scalars = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_scalars.all.return_value = expected_items
        
        # Act
        result = await base_service.get_multi(
            db=mock_db_session,
            skip=skip,
            limit=limit
        )
        
        # Assert
        assert result == expected_items
        mock_db_session.execute.assert_called_once()
        
        # Verify that execute was called with the expected arguments
        # Check the query structure in a way that's compatible with SQLAlchemy's internals
        args, kwargs = mock_db_session.execute.call_args
        
        # The first argument should be a select statement
        select_stmt = args[0]
        
        # Convert the select statement to a string and check for expected components
        query_str = str(select_stmt).upper()
        assert 'SELECT' in query_str
        assert 'FROM' in query_str
        assert 'TEST_MODEL' in query_str
        assert 'ORDER BY' in query_str
        assert 'DESC' in query_str
        
        # Check for LIMIT in the query - it might be parameterized or not
        assert 'LIMIT' in query_str
