from app.langchain.model import get_response
from app.core import logger

logger.info("Console chat. Type 'exit' to finish.")
while True:
    msg = input("You: ")
    if msg.lower() == "exit":
        break
    print("Bot:", get_response(msg))
