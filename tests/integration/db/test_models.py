"""Integration tests for database models."""
import asyncio
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from app.db.models.chat import Chat, Intent as ChatIntent
from app.db.models.message import Message, Sender, Intent as MessageIntent

pytestmark = pytest.mark.asyncio

class TestChatModel:
    """Test cases for the Chat model."""
    
    async def test_create_chat(self, db_session):
        """Test creating a new chat."""
        # Create a new chat
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        
        # Add the chat to the session
        db_session.add(chat)
        await db_session.flush()
        
        # Verify the chat was created with correct attributes
        assert chat.id is not None
        assert isinstance(chat.id, str)
        assert len(chat.id) > 0
        assert chat.client_name == "Test User"
        assert chat.client_email == "test@example.com"
        assert chat.initial_intent == ChatIntent.GENERAL_QUESTION
        assert chat.created_at is not None
        assert chat.updated_at is None  # Should be None until updated
        assert chat.transferred_to_operator is False
        assert chat.transfer_inquiry_id is None
        assert chat.transfer_query is None
        assert chat.operator_transfer_time is None
        
        # Verify we can retrieve the chat
        result = await db_session.execute(select(Chat).filter_by(id=chat.id))
        retrieved_chat = result.scalars().first()
        assert retrieved_chat is not None
        assert retrieved_chat.id == chat.id
        
        # Verify messages relationship is empty by refreshing the object
        await db_session.refresh(chat, ['messages'])
        assert len(chat.messages) == 0
    
    async def test_chat_relationships(self, db_session):
        """Test chat relationships with messages."""
        # Create a chat
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION,
            transfer_inquiry_id="test-inquiry-123",
            transfer_query="Test query",
            transferred_to_operator=True
        )
        db_session.add(chat)
        await db_session.flush()
        
        # Create messages for the chat
        message1 = Message(
            chat_id=chat.id,
            content="Hello, I have a question",
            sender=Sender.CLIENT,
            intent=MessageIntent.GREETING
        )
        message2 = Message(
            chat_id=chat.id,
            content="How can I help you?",
            sender=Sender.BOT,
            intent=MessageIntent.GREETING
        )
        
        db_session.add_all([message1, message2])
        await db_session.flush()
        
        # Verify the chat attributes
        assert chat is not None
        assert chat.client_name == "Test User"
        assert chat.transfer_inquiry_id == "test-inquiry-123"
        assert chat.transfer_query == "Test query"
        assert chat.transferred_to_operator is True
        
        # Query the messages for this chat
        result = await db_session.execute(
            select(Message)
            .filter(Message.chat_id == chat.id)
            .order_by(Message.content)
        )
        messages = result.scalars().all()
        
        # Verify the messages
        assert len(messages) == 2
        
        # Verify message 1
        assert messages[0].content == "Hello, I have a question"
        assert messages[0].sender == Sender.CLIENT
        assert messages[0].intent == MessageIntent.GREETING
        assert messages[0].chat_id == chat.id
        
        # Verify message 2
        assert messages[1].content == "How can I help you?"
        assert messages[1].sender == Sender.BOT
        assert messages[1].intent == MessageIntent.GREETING
        assert messages[1].chat_id == chat.id


class TestMessageModel:
    """Test cases for the Message model."""
    
    async def test_create_message(self, db_session):
        """Test creating a new message."""
        # Create a chat first
        chat = Chat(
            client_name="Test User",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        
        # Create a message with all fields
        test_content = "Test message with special chars: áéíóú 123"
        message = Message(
            chat_id=chat.id,
            content=test_content,
            sender=Sender.CLIENT,
            intent=MessageIntent.GREETING
        )
        
        # Get timestamps with timezone info for comparison
        before_creation = datetime.utcnow()
        db_session.add(message)
        await db_session.flush()
        after_creation = datetime.utcnow()
        
        # Verify the message was created with correct attributes
        assert message.id is not None
        assert isinstance(message.id, str)
        assert len(message.id) > 0
        assert message.content == test_content
        assert message.sender == Sender.CLIENT
        assert message.intent == MessageIntent.GREETING
        assert message.chat_id == chat.id
        
        # Verify timestamps - ensure timezone-aware comparison
        assert message.created_at is not None
        
        # Convert created_at to timezone-naive UTC if it's timezone-aware
        created_at = message.created_at.replace(tzinfo=None) if message.created_at.tzinfo else message.created_at
        
        # Allow for slight timing differences (up to 1 second) to account for test execution time
        assert created_at >= (before_creation - timedelta(seconds=1)), \
            f"Created at {created_at} is not after or equal to {before_creation}"
        assert created_at <= (after_creation + timedelta(seconds=1)), \
            f"Created at {created_at} is not before or equal to {after_creation}"
    
    async def test_message_relationships(self, db_session):
        """Test message relationships with chat."""
        # Create a chat with some attributes
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        
        # Create a message
        message = Message(
            chat_id=chat.id,
            content="Test message with relationship",
            sender=Sender.CLIENT,
            intent=MessageIntent.GREETING
        )
        db_session.add(message)
        await db_session.flush()
        
        # Verify the relationship
        assert message.chat is not None
        assert message.chat.id == chat.id
        assert message.chat.client_name == "Test User"
        assert message.chat.initial_intent == ChatIntent.GENERAL_QUESTION


class TestModelQueries:
    """Test database queries with models."""
    
    async def test_query_chat_with_messages(self, db_session):
        """Test querying a chat with its messages."""
        # Create a chat with attributes
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        
        # Create some messages with different senders and intents
        messages_data = [
            {"content": "Hello!", "sender": Sender.CLIENT, "intent": MessageIntent.GREETING},
            {"content": "How can I help?", "sender": Sender.BOT, "intent": MessageIntent.GREETING},
            {"content": "Do you have product X?", "sender": Sender.CLIENT, "intent": MessageIntent.PRODUCT_DETAILS},
            {"content": "Yes, we have product X in stock.", "sender": Sender.BOT, "intent": MessageIntent.PRODUCT_DETAILS},
            {"content": "What's the price?", "sender": Sender.CLIENT, "intent": MessageIntent.PRODUCT_DETAILS}
        ]
        
        messages = []
        for msg_data in messages_data:
            message = Message(
                chat_id=chat.id,
                content=msg_data["content"],
                sender=msg_data["sender"],
                intent=msg_data["intent"]
            )
            db_session.add(message)
            messages.append(message)
        
        await db_session.flush()
        
        # Query the messages directly
        result = await db_session.execute(
            select(Message)
            .filter(Message.chat_id == chat.id)
        )
        queried_messages = result.scalars().all()
        
        # Verify the query results
        assert len(queried_messages) == len(messages_data)
        
        # Verify message contents and attributes
        message_contents = {msg.content for msg in queried_messages}
        expected_contents = {msg["content"] for msg in messages_data}
        assert message_contents == expected_contents
        
        # Verify message attributes
        for msg in queried_messages:
            assert msg.id is not None
            assert isinstance(msg.id, str)
            assert msg.chat_id == chat.id
            assert msg.content in expected_contents
            assert msg.sender in [Sender.CLIENT, Sender.BOT]
            assert msg.intent in [MessageIntent.GREETING, MessageIntent.PRODUCT_DETAILS]
            assert msg.created_at is not None
    
    async def test_message_timestamps(self, db_session):
        """Test that message timestamps are set correctly."""
        chat = Chat(
            client_name="Test User",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        
        # Create multiple messages with a small delay to test ordering
        messages = []
        for i in range(3):
            before_creation = datetime.utcnow()
            await asyncio.sleep(0.1)  # Increased delay to ensure different timestamps
            message = Message(
                chat_id=chat.id,
                content=f"Test message {i}",
                sender=Sender.CLIENT,
                intent=MessageIntent.GENERAL_QUESTION
            )
            db_session.add(message)
            await db_session.flush()
            after_creation = datetime.utcnow()
            
            # Verify timestamp is set and within expected range
            assert message.created_at is not None
            
            # Convert created_at to timezone-naive UTC if it's timezone-aware
            created_at = message.created_at.replace(tzinfo=None) if message.created_at.tzinfo else message.created_at
            
            # Allow for slight timing differences (up to 1 second)
            assert created_at >= (before_creation - timedelta(seconds=1)), \
                f"Message {i}: Created at {created_at} is not after or equal to {before_creation}"
            assert created_at <= (after_creation + timedelta(seconds=1)), \
                f"Message {i}: Created at {created_at} is not before or equal to {after_creation}"
                
            messages.append(message)
        
        # Test query ordering
        result = await db_session.execute(
            select(Message)
            .filter(Message.chat_id == chat.id)
            .order_by(Message.created_at)
        )
        queried_messages = result.scalars().all()
        
        # Verify messages are in chronological order
        assert len(queried_messages) == 3
        for i in range(1, len(queried_messages)):
            assert queried_messages[i-1].created_at <= queried_messages[i].created_at, \
                f"Message {i-1} should be before message {i} in results"
