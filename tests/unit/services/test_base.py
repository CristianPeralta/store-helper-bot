"""Tests for the BaseService class."""
import pytest
from unittest.mock import MagicMock
from pydantic import BaseModel

class MockCreateSchema(BaseModel):
    """Mock schema for testing."""
    name: str
    description: str = ""
    value: int = 0

class MockUpdateSchema(BaseModel):
    """Mock update schema for testing."""
    name: str
    value: int

@pytest.mark.asyncio
class TestBaseService:
    """Test cases for BaseService."""
    
    async def test_get_existing_item(self, base_service, mock_db_session, test_db_object):
        """Test getting an existing item by ID."""
        # Configurar el mock para devolver un resultado
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = test_db_object
        mock_db_session.execute.return_value = mock_result
        
        # Ejecutar
        result = await base_service.get(mock_db_session, id=1)
        
        # Verificar
        assert result == test_db_object
        mock_db_session.execute.assert_called_once()
        # Verificar que se llamó a execute con la consulta correcta
        args, _ = mock_db_session.execute.call_args
        assert hasattr(args[0], 'whereclause')  # Verificar que se creó una cláusula WHERE
        assert 'id = :id_1' in str(args[0])  # Verificar que se está filtrando por ID
        
    async def test_get_nonexistent_item(self, base_service, mock_db_session):
        """Test getting a non-existent item returns None."""
        # Configurar el mock para devolver None
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Ejecutar
        result = await base_service.get(mock_db_session, id=999)
        
        # Verificar
        assert result is None
        
    async def test_create_item(self, base_service, mock_db_session):
        """Test creating a new item."""
        # Datos de prueba
        item_data = MockCreateSchema(name="Test Item", description="Test Description", value=42)
        
        # Ejecutar
        result = await base_service.create(mock_db_session, obj_in=item_data)
        
        # Verificar
        assert result is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once()
        
    async def test_update_item(self, base_service, mock_db_session, test_db_object):
        """Test updating an existing item."""
        # Datos de prueba
        update_data = MockUpdateSchema(name="Updated Name", value=100)
        
        # Ejecutar
        result = await base_service.update(
            mock_db_session,
            db_obj=test_db_object,
            obj_in=update_data
        )
        
        # Verificar
        assert result == test_db_object
        assert test_db_object.name == "Updated Name"
        assert test_db_object.value == 100
        mock_db_session.add.assert_called_once_with(test_db_object)
        mock_db_session.commit.assert_awaited_once()
        mock_db_session.refresh.assert_awaited_once_with(test_db_object)
        
    async def test_remove_item(self, base_service, mock_db_session, test_db_object):
        """Test removing an item."""
        # Configurar el mock para devolver un objeto
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = test_db_object
        mock_db_session.execute.return_value = mock_result
        
        # Ejecutar
        result = await base_service.remove(mock_db_session, id=1)
        
        # Verificar
        assert result == test_db_object
        mock_db_session.delete.assert_called_once_with(test_db_object)
        mock_db_session.commit.assert_awaited_once()
        
    async def test_remove_nonexistent_item(self, base_service, mock_db_session):
        """Test removing a non-existent item returns None."""
        # Configurar el mock para devolver None
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Ejecutar
        result = await base_service.remove(mock_db_session, id=999)
        
        # Verificar
        assert result is None
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()
