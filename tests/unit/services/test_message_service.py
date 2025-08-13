"""Tests for the MessageService class."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import declarative_base
from app.services.message import MessageService
from app.schemas.message import MessageListQuery, SenderEnum, IntentEnum

# Create a base class for test models with a name that doesn't start with 'Test'
# and add __test__ = False to prevent pytest from collecting it
TestBase = declarative_base()
TestBase.__test__ = False  # Prevent pytest from collecting the base class

class TestMessage(TestBase):
    """Test message model for MessageService tests."""
    __tablename__ = 'test_messages'
    __test__ = False  # Tell pytest this is not a test class
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    sender = Column(Enum(SenderEnum), nullable=False)
    intent = Column(Enum(IntentEnum), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

@pytest.mark.asyncio
class TestMessageService:
    """Test cases for MessageService."""
    
    @pytest.fixture
    def message_service(self):
        """Create a MessageService instance for testing."""
        return MessageService(TestMessage)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def test_messages(self):
        """Create test messages with string chat_ids to match schema."""
        return [
            TestMessage(
                id="msg-1",
                chat_id="chat-1",
                content="Hello",
                sender=SenderEnum.CLIENT,
                intent=IntentEnum.GREETING,
                created_at=datetime.utcnow()
            ),
            TestMessage(
                id="msg-2",
                chat_id="chat-1",
                content="Hi there!",
                sender=SenderEnum.BOT,
                intent=IntentEnum.GREETING,
                created_at=datetime.utcnow()
            ),
            TestMessage(
                id="msg-3",
                chat_id="chat-2",
                content="Product info",
                sender=SenderEnum.CLIENT,
                intent=IntentEnum.STORE_INFO,
                created_at=datetime.utcnow()
            ),
        ]
    
    async def test_get_messages_with_filters(self, message_service, mock_db_session, test_messages):
        """Test getting messages with various filters."""
        # Configure the mock to return test messages
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = test_messages
        mock_db_session.execute.return_value = mock_result
        
        # Query parameters - using string chat_id to match schema
        query_params = MessageListQuery(
            chat_id="chat-1",
            sender=SenderEnum.CLIENT,
            intent=IntentEnum.GREETING,
            sort_by="created_at",
            sort_order="desc"
        )
        
        # Execute
        result = await message_service.get_messages(
            mock_db_session,
            query_params=query_params
        )
        
        # Verify
        assert len(result) == 3  # Should return all test messages
        mock_db_session.execute.assert_called_once()
        
        # Verify the correct query was built
        args, _ = mock_db_session.execute.call_args
        query = args[0]
        
        # Check that the query has the expected filters
        assert hasattr(query, 'whereclause')
        where_str = str(query.whereclause).lower()
        assert 'chat_id' in where_str
        assert 'sender' in where_str
        assert 'intent' in where_str
        
        # Check ordering - verify the query has an order_by clause
        assert hasattr(query, '_order_by_clause')
        # Convert order_by_clause to string for easier inspection
        order_by_str = str(query._order_by_clause).lower()
        # Check for descending order in any part of the order by clause
        assert 'desc' in order_by_str, f"Expected 'desc' in order by clause, got: {order_by_str}"
    
    async def test_get_messages_with_date_filters(self, message_service, mock_db_session, test_messages):
        """Test getting messages with date filters."""
        # Configure the mock to return test messages
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = test_messages
        mock_db_session.execute.return_value = mock_result
        
        # Date range for filtering
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        # Query parameters
        query_params = MessageListQuery(
            chat_id="chat-1",  # Adding chat_id to match required fields
            start_date=start_date,
            end_date=end_date,
            sort_by="created_at",
            sort_order="asc"
        )
        
        # Execute
        result = await message_service.get_messages(
            mock_db_session,
            query_params=query_params
        )
        
        # Verify
        assert len(result) == 3
        mock_db_session.execute.assert_called_once()
        
        # Verify the correct query was built with date filters
        args, _ = mock_db_session.execute.call_args
        query = args[0]
        
        # Check that the query has the expected date filters
        assert hasattr(query, 'whereclause')
        where_str = str(query.whereclause).lower()
        assert 'created_at >=' in where_str
        assert 'created_at <=' in where_str
        
        # Check ordering is ascending
        order_by = str(query._order_by_clause).lower()
        assert 'asc' in order_by
