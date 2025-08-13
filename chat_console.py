import logging
from app.services.chat import chat_service
from app.schemas.chat import ChatCreate
from app.db.silent_session import get_db_session
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