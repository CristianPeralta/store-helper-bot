import logging
from app.services.chat import chat_service
from app.services.message import message_service
from app.schemas.chat import ChatCreate
from app.schemas.message import MessageCreate, SenderEnum, MessageUpdate, IntentEnum
from app.db.silent_session import get_db_session
from app.langchain.model import StoreAssistant, State
from app.services.chat_processor import ChatProcessor

"""
Console runner for the Store Helper chatbot.

This script demonstrates how to:
- Create and persist a chat session in the DB
- Read user input from console and send it to the assistant
- Persist messages with intents
- Provide robust error handling and clear user feedback

It is intentionally written as an educational example for engineering students.
"""

# Configure structured logging instead of disabling it. In an educational setting,
# logs are useful to understand the flow and to debug issues. Adjust the level if needed.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

print("\n" + "="*50)
print("  Store Helper Chat - Type 'exit' to quit")
print("="*50 + "\n")

async def _read_input(prompt: str) -> str:
    """Read input in a way that doesn't block the event loop."""
    try:
        import asyncio
        return await asyncio.to_thread(input, prompt)
    except Exception:  # Fallback to direct input if to_thread is unavailable
        return input(prompt)


async def _process_turn(
    assistant: StoreAssistant,
    db,
    state: State,
    user_input: str,
) -> None:
    """Process a single user-assistant exchange with persistence and error handling."""
    # Save user message
    user_message = await message_service.create(
        db,
        obj_in=MessageCreate(
            chat_id=state["chat_id"],
            content=user_input,
            sender=SenderEnum.CLIENT,
        )
    )

    # Add user message to conversation history
    state["messages"].append({"role": "user", "content": user_input})

    # Get bot response using the same assistant instance
    response = await assistant.get_response_by_thread_id(state["chat_id"], state)

    # Validate response structure defensively
    content = response.get("content") if isinstance(response, dict) else None
    intent_value = response.get("intent") if isinstance(response, dict) else IntentEnum.OTHER
    if not isinstance(content, str) or not content:
        content = "I couldn't generate a response. Please try again or rephrase your question."
        logger.warning("Assistant returned empty or invalid content: %s", response)

    try:
        # Try to coerce the model-provided intent to our Enum (by value)
        intent_enum = IntentEnum(intent_value.upper())
    except Exception:
        # If casting fails, default to OTHER
        intent_enum = IntentEnum.OTHER

    print("\nBot:", content)

    # Add assistant's response to conversation history
    state["messages"].append({"role": "assistant", "content": content})

    # Save bot response and update user's message intent
    await message_service.create(
        db,
        obj_in=MessageCreate(
            chat_id=state["chat_id"],
            content=content,
            sender=SenderEnum.BOT,
            intent=intent_enum,
        )
    )
    await message_service.update(
        db,
        db_obj=user_message,
        obj_in=MessageUpdate(
            intent=intent_enum,
        ),
    )

    # Commit after each exchange
    await db.commit()


async def main() -> None:
    """Entry point: creates a chat session and runs a console REPL against the assistant."""
    # Get a new async session from our silent session factory
    async with get_db_session() as db:
        # Create a new chat
        chat = await chat_service.create(
            db,
            obj_in=ChatCreate()
        )
        
        # Initialize the chat processor with the database session
        chat_processor = ChatProcessor(db=db)
        
        # Initialize messages with system message
        state = {
            "chat_id": str(chat.id),
            "messages": [],
            "name": "",
            "email": "",
            "last_inquiry_id": None
        }
        try:
            while True:
                try:
                    user_input = await _read_input("You: ")
                    if user_input is None:
                        print("\nNo input detected. Type 'exit' to quit.")
                        continue
                    if user_input.strip().lower() in ["quit", "exit", "q"]:
                        print(f"\nGoodbye! Your chat ID is: {chat.id}")
                        break

                    # Empty message guard
                    if not user_input.strip():
                        print("(Tip) You sent an empty message. Please type your question.")
                        continue

                    # Process the message through the chat processor
                    await chat_processor.process_message(state, user_input)

                except KeyboardInterrupt:
                    print(f"\nInterrupted. Your chat ID is: {chat.id}")
                    break
                except Exception as e:
                    logger.exception("An error occurred during the chat loop")
                    print(f"\nAn error occurred: {str(e)}\n")
                    try:
                        await db.rollback()
                    except Exception:
                        logger.error("Failed to rollback the transaction after an error.")
                    
        finally:
            await db.close()

if __name__ == "__main__":
    # Disable warnings before running
    import warnings
    warnings.filterwarnings("ignore")
    
    # Run the main function
    import asyncio
    asyncio.run(main())