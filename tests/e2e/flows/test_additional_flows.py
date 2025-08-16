"""End-to-end tests for additional conversation flows.

This module contains tests for the following intents:
- GREETING: Greetings and salutations
- GENERAL_QUESTION: General questions
- OTHER: Unrecognized queries
"""
import pytest
from httpx import AsyncClient
from fastapi import status

from app.db.models.message import Sender, Intent as MessageIntent

class BaseAdditionalFlowsTest:
    """Base class with common test methods for additional conversation flows."""
    
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
        return response.json()
    
    async def send_message(self, async_client: AsyncClient, chat_id: str, content: str, intent: str):
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
            "/api/messages/",
            params={"chat_id": chat_id, "sort_order": "asc"}
        )
        assert response.status_code == status.HTTP_200_OK, f"Failed to get messages: {response.text}"
        return response.json()

# Tests for GREETING intent

class TestGreetingFlow(BaseAdditionalFlowsTest):
    """Test greeting flows."""
    
    @pytest.mark.parametrize(
        "user_message,expected_keywords",
        [
            ("Hello!", ["hello", "hi", "welcome"]),
            ("Hi there!", ["hello", "hi", "welcome"]),
            ("Good morning!", ["morning", "hello", "welcome"]),
            ("Good afternoon!", ["afternoon", "hello", "welcome"]),
            ("Good evening!", ["evening", "hello", "welcome"]),
        ]
    )
    @pytest.mark.asyncio
    async def test_greeting_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        expected_keywords: list[str]
    ):
        """Test greeting flow with different greeting messages."""
        # Create a new chat
        chat_id = await create_chat
        
        # Send greeting message
        response = await self.send_message(
            async_client=async_client,
            chat_id=chat_id,
            content=user_message,
            intent=MessageIntent.GREETING.value
        )
        
        # Verify the message was sent successfully
        assert response.status_code == status.HTTP_201_CREATED
        
        # Get the chat messages
        messages = await self.get_chat_messages(async_client, chat_id)
        
        # Verify the bot responded
        assert len(messages) >= 2, "Expected at least 2 messages (user + bot response)"
        
        # Get the bot's response
        bot_response = messages[-1]["content"].lower()
        
        # Verify the response contains expected keywords
        assert any(keyword in bot_response for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}, but got: {bot_response}"

# Tests for GENERAL_QUESTION intent

class TestGeneralQuestionFlow(BaseAdditionalFlowsTest):
    """Test general question flows."""
    
    @pytest.mark.parametrize(
        "user_message,expected_keywords",
        [
            ("How are you?", ["assistant", "help", "today"]),
            ("What can you do?", ["help", "assist", "products", "store"]),
            ("Tell me about yourself", ["assistant", "help", "store"]),
            ("Who made you?", ["created", "developed", "team", "creator", "made", "who"]),
        ]
    )
    @pytest.mark.asyncio
    async def test_general_question_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        expected_keywords: list[str]
    ):
        """Test general question flow with different questions."""
        # Create a new chat
        chat_id = await create_chat
        
        # Send general question
        response = await self.send_message(
            async_client=async_client,
            chat_id=chat_id,
            content=user_message,
            intent=MessageIntent.GENERAL_QUESTION.value
        )
        
        # Verify the message was sent successfully
        assert response.status_code == status.HTTP_201_CREATED
        
        # Get the chat messages
        messages = await self.get_chat_messages(async_client, chat_id)
        
        # Verify the bot responded
        assert len(messages) >= 2, "Expected at least 2 messages (user + bot response)"
        
        # Get the bot's response
        bot_response = messages[-1]["content"].lower()
        
        # Verify the response contains expected keywords
        assert any(keyword in bot_response for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}, but got: {bot_response}"

# Tests for OTHER intent

class TestOtherFlow(BaseAdditionalFlowsTest):
    """Test handling of unrecognized queries."""
    
    @pytest.mark.parametrize(
        (
            "user_message",
            "expected_keywords"
        ),
        [
            (
                "asdfghjkl",
                [
                    "typo", "mistake", "clarify", "question", "help", "understand",
                    "something else", "unclear", "accident", "valid", "unintended",
                    "random", "text", "test", "unintended", "understand", "clarify",
                    "typo", "string", "characters"
                ]
            ),
            (
                "Random gibberish",
                [
                    "unrelated", "rephrase", "ask a question", "random", "text",
                    "help", "sense", "mistake", "unclear", "test", "unintended",
                    "understand", "valid", "clarify"
                ]
            ),
            (
                "1234567890",
                [
                    "numbers", "understand", "help", "clarify", "mistake",
                    "unclear", "number", "recognized", "digit", "unintended",
                    "understand", "valid", "numeric"
                ]
            ),
            (
                "!@#$%^&*()",
                [
                    "special", "characters", "understand", "help", "clarify",
                    "symbols", "something else", "mistake", "unclear", "accident",
                    "valid", "unintended", "clarify", "unintended", "understand",
                    "clarify", "typo"
                ]
            )
        ]
    )
    @pytest.mark.asyncio
    async def test_other_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        expected_keywords: list[str]
    ):
        """Test handling of unrecognized queries."""
        # Create a new chat
        chat_id = await create_chat
        
        # Send unrecognized message
        response = await self.send_message(
            async_client=async_client,
            chat_id=chat_id,
            content=user_message,
            intent=MessageIntent.OTHER.value
        )
        
        # Verify the message was sent successfully
        assert response.status_code == status.HTTP_201_CREATED
        
        # Get the chat messages
        messages = await self.get_chat_messages(async_client, chat_id)
        
        # Verify the bot responded
        assert len(messages) >= 2, "Expected at least 2 messages (user + bot response)"
        
        # Get the bot's response
        bot_response = messages[-1]["content"].lower()
        
        # Verify the response contains expected keywords
        assert any(keyword in bot_response for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}, but got: {bot_response}"
