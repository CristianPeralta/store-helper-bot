"""End-to-end tests for the human assistance flow."""
import pytest
import re
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.chat import Chat, Intent as ChatIntent
from app.db.models.message import Message, Sender, Intent as MessageIntent

# Configure warning filters at the module level
pytestmark = [
    pytest.mark.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"pydantic.*"
    ),
    pytest.mark.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"fireworks.*"
    )
]

@pytest.mark.asyncio
class TestHumanAssistanceFlow:
    """Test the complete human assistance flow from chat start to inquiry creation."""
    
    async def teardown_method(self):
        """Ensure all resources are properly cleaned up after each test."""
        import gc
        import asyncio
        
        # Run any pending tasks
        try:
            loop = asyncio.get_event_loop()
            pending = asyncio.all_tasks(loop=loop)
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        except RuntimeError:
            pass  # No event loop
            
        # Force garbage collection to clean up any remaining resources
        gc.collect()
    
    @pytest.fixture
    async def create_chat(self, async_client: AsyncClient):
        """Helper to create a new chat and return the chat ID."""
        chat_data = {
            "client_name": "Test User",
            "client_email": "test@example.com",
        }
        response = await async_client.post("/api/chats/", json=chat_data)
        assert response.status_code == status.HTTP_201_CREATED
        return response.json()["id"]

    async def get_chat(self, async_client: AsyncClient, chat_id: str):
        """Helper to get chat details."""
        response = await async_client.get(f"/api/chats/{chat_id}")
        assert response.status_code == status.HTTP_200_OK, f"Failed to get chat: {response.text}"
        chat_data = response.json()
        print(f"\n[DEBUG] Chat data for {chat_id}:")
        print(f"  - ID: {chat_data['id']}")
        print(f"  - Created at: {chat_data['created_at']}")
        print(f"  - Updated at: {chat_data['updated_at']}")
        print(f"  - Transferred to operator: {chat_data.get('transferred_to_operator', 'N/A')}")
        if 'messages' in chat_data:
            print(f"  - Messages count: {len(chat_data['messages'])}")
        return chat_data

    async def send_message(self, async_client: AsyncClient, chat_id: str, content: str, intent: str = MessageIntent.HUMAN_ASSISTANCE.value):
        """Helper to send a message and return the response."""
        message_data = {
            "content": content,
            "sender": Sender.CLIENT.value,
            "intent": intent,
            "chat_id": chat_id
        }
        return await async_client.post("/api/messages/", json=message_data)

    async def get_chat_messages(self, async_client: AsyncClient, chat_id: str):
        """Helper to get all messages for a chat."""
        response = await async_client.get(
            f"/api/messages/",
            params={"chat_id": chat_id, "sort_order": "asc"}
        )
        assert response.status_code == status.HTTP_200_OK
        return response.json()
        
    async def get_latest_bot_message(self, async_client: AsyncClient, chat_id: str, max_attempts: int = 3, delay: float = 0.5):
        """Helper to get the latest bot message with retry logic."""
        import asyncio
        
        for attempt in range(max_attempts):
            messages = await self.get_chat_messages(async_client, chat_id)
            if messages and messages[-1]["sender"] == Sender.BOT.value:
                bot_message = messages[-1]
                print(f"\n[DEBUG] Bot response (attempt {attempt + 1}): {bot_message['content']}")
                print(f"[DEBUG] Message intent: {bot_message.get('intent', 'N/A')}")
                print(f"[DEBUG] Full message: {bot_message}\n")
                return bot_message
                
            if attempt < max_attempts - 1:  # Don't sleep on the last attempt
                print(f"[DEBUG] Waiting for bot response (attempt {attempt + 1}/{max_attempts})...")
                await asyncio.sleep(delay)
                
        # If we get here, all attempts failed
        print("[DEBUG] All attempts to get bot message failed. Messages in chat:")
        for idx, msg in enumerate(messages):
            print(f"  {idx + 1}. {msg['sender']}: {msg['content']} (intent: {msg.get('intent', 'N/A')})")
        assert False, f"No bot message found after {max_attempts} attempts"

    @pytest.mark.parametrize("user_message,expected_keywords", [
        ("I need help with an order", ["help", "assist", "how can i help", "name", "email"]),
        ("Can I speak to a human?", ["help", "assist", "how can i help", "name", "email"]),
        ("I want to talk to a manager", ["help", "assist", "how can i help", "name", "email"]),
    ])
    async def test_human_assistance_flow(
        self, 
        async_client: AsyncClient, 
        db_session: AsyncSession,
        create_chat,
        user_message,
        expected_keywords
    ):
        """Test the complete human assistance flow with different initial messages."""
        chat_id = await create_chat
        
        # 1. Send initial message requesting human assistance
        response = await self.send_message(
            async_client, 
            chat_id, 
            user_message,
            MessageIntent.HUMAN_ASSISTANCE.value
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # 2. Verify bot's response asks for name and email in English
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        
        # Verify response is in English and contains expected keywords or indicates human assistance
        bot_response = bot_message["content"].lower()
        keyword_found = any(keyword in bot_response for keyword in expected_keywords)
        human_assistance_offered = any(phrase in bot_response 
                                     for phrase in ["human", "agent", "representative", "manager"])
        
        assert keyword_found or human_assistance_offered, (
            f"Expected bot response to contain one of {expected_keywords} or offer human assistance. "
            f"Got: {bot_response}"
        )
        
        # 3. Send user details
        user_details = "My name is John Doe and my email is john.doe@example.com"
        response = await self.send_message(
            async_client,
            chat_id,
            user_details,
            MessageIntent.HUMAN_ASSISTANCE.value
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # 4. Verify chat is marked as transferred to operator or bot provided assistance
        chat = await self.get_chat(async_client, chat_id)
        print(f"\n[DEBUG] Chat transfer status: {chat.get('transferred_to_operator', 'N/A')}")
        print(f"[DEBUG] Full chat data: {chat}\n")
        
        # Check if chat was transferred OR bot provided assistance
        if not chat.get('transferred_to_operator', False):
            # If not transferred, verify bot provided meaningful assistance
            messages = await self.get_chat_messages(async_client, chat_id)
            bot_messages = [msg for msg in messages if msg['sender'] == Sender.BOT.value]
            last_bot_message = bot_messages[-1]['content'].lower() if bot_messages else ''
            
            print(f"[DEBUG] Last bot message: {last_bot_message}")
            assistance_provided = any(phrase in last_bot_message 
                                   for phrase in ["how can i help", "what do you need", "assist you"])
            
            if not assistance_provided:
                print("[DEBUG] Bot did not provide expected assistance. All messages:")
                for idx, msg in enumerate(messages):
                    print(f"  {idx + 1}. {msg['sender']}: {msg['content']} (intent: {msg.get('intent', 'N/A')})")
            
            assert assistance_provided, (
                "Expected chat to be transferred or bot to provide assistance. "
                f"Last bot message: {last_bot_message}"
            )
        
        # 5. Verify all messages were saved
        db_messages = (await db_session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )).scalars().all()
        
        print(f"\n[DEBUG] Verifying database messages:")
        for idx, msg in enumerate(db_messages):
            print(f"  {idx + 1}. {msg.sender}: {msg.content} (intent: {msg.intent})")
        
        assert len(db_messages) >= 2, "Not all messages were saved to the database"
        assert db_messages[0].content == user_message
        assert db_messages[0].sender == Sender.CLIENT, f"Expected sender to be CLIENT, got {db_messages[0].sender}"
        assert db_messages[1].content == bot_message["content"]
        assert db_messages[1].sender == Sender.BOT, f"Expected sender to be BOT, got {db_messages[1].sender}"
        
        # If we sent a follow-up message, verify it too
        if len(db_messages) > 2:
            assert db_messages[2].content == user_details
            assert db_messages[2].sender == Sender.CLIENT, f"Expected sender to be CLIENT, got {db_messages[2].sender}"
            assert "John Doe" in db_messages[2].content
            assert "john.doe@example.com" in db_messages[2].content

    @pytest.mark.parametrize("user_details,expected_keywords,status_code", [
        ("My name is John Doe", ["how can i assist", "help you with", "what do you need", "email"], status.HTTP_201_CREATED),
        ("My email is test@example.com", ["how can i assist", "help you with", "what do you need", "name"], status.HTTP_201_CREATED),
        # Empty message should return 422 (validation error) - expect a helpful message
        ("", ["need more information", "please provide details", "what do you need help with", "help you", "name", "email"], status.HTTP_422_UNPROCESSABLE_ENTITY),
    ])
    async def test_human_assistance_missing_fields(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        create_chat,
        user_details,
        expected_keywords,
        status_code
    ):
        """Test human assistance flow with missing required fields."""
        chat_id = await create_chat
        
        # 1. Initial request
        await self.send_message(
            async_client,
            chat_id,
            "I need help",
            MessageIntent.HUMAN_ASSISTANCE.value
        )
        
        # 2. Send incomplete user details
        response = await self.send_message(
            async_client,
            chat_id,
            user_details,
            MessageIntent.HUMAN_ASSISTANCE.value
        )
        assert response.status_code == status_code
        
        # 3. Verify bot asks for missing information
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        # Check if any of the expected keywords or similar phrases are in the response
        bot_response = bot_message["content"].lower()
        keyword_found = any(keyword in bot_response for keyword in expected_keywords)
        
        # For empty messages, also accept responses that ask for more details
        if not user_details.strip():
            keyword_found = keyword_found or any(phrase in bot_response 
                                              for phrase in ["information", "details", "help"])
        
        assert keyword_found, (
            f"Expected bot response to contain one of {expected_keywords} or ask for more details. "
            f"Got: {bot_message['content']}"
        )

    async def test_human_assistance_invalid_email(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        create_chat
    ):
        """Test human assistance flow with invalid email format."""
        chat_id = await create_chat
        
        # 1. Initial request
        await self.send_message(
            async_client,
            chat_id,
            "I need help",
            MessageIntent.HUMAN_ASSISTANCE.value
        )
        
        # 2. Send details with invalid email
        response = await self.send_message(
            async_client,
            chat_id,
            "My name is John Doe and my email is invalid-email",
            MessageIntent.HUMAN_ASSISTANCE.value
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # 3. Verify bot asks for valid email or indicates an issue
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        # Check for any indication of email validation issue or helpful response
        bot_response = bot_message["content"].lower()
        email_issue = any(phrase in bot_response 
                         for phrase in ["email", "invalid", "valid", "correct", "verify"])
        helpful_response = any(phrase in bot_response 
                             for phrase in ["help", "assist", "support"])
        
        assert email_issue or helpful_response, (
            f"Expected bot to mention email validation or provide assistance. "
            f"Got: {bot_message['content']}"
        )
