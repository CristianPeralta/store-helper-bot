import os
from langchain.chat_models import init_chat_model
from langchain.schema import HumanMessage
from app.core import get_settings

# Initialize settings
settings = get_settings()

os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

model = init_chat_model("gemini-2.0-flash", model_provider="google_genai")

def get_response(user_input: str) -> str:
    response = model.invoke([HumanMessage(content=user_input)])
    return response.content
