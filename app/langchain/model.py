import os
import re
from langchain.chat_models import init_chat_model
import json
from app.core import get_settings
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph
from langchain_core.tools import tool
# Initialize settings
settings = get_settings()

os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

llm = init_chat_model("gemini-2.0-flash", model_provider="google_genai")

@tool
def human_assistance(query: str) -> str:
    """Request assistance from a human."""
    human_response = interrupt({"query": query})
    return human_response["data"]

class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)

config = {"configurable": {"thread_id": "1"}}

graph_builder.set_entry_point("chatbot")
memory = InMemorySaver()
graph = graph_builder.compile(checkpointer=memory)

def run_graph_once_with_interrupt(user_input: str):
    system_message = {
        "role": "system",
        "content": (
            "You are an assistant that always responds in JSON format with the following fields:\n"
            "- `reply`: your natural language response to the user\n"
            "- `intent`: a single word identifying the user's intent\n\n"
            "You must classify the user's intent using **only one** of the following categories:\n"
            "- product_inquiry\n"
            "- general_question\n"
            "- greeting\n"
            "- other\n\n"
            "Always respond in this exact JSON format:\n"
            "{\"reply\": \"<your reply here>\", \"intent\": \"<one of the above categories>\"}\n\n"
            "Example:\n"
            "User: 'Hi there!'\n"
            "Response: {\"reply\": \"Hello! How can I assist you today?\", \"intent\": \"greeting\"}"
        )
    }
    result = graph.invoke(
        {"messages": [system_message, {"role": "user", "content": user_input}]},
        config=config,
    )

    # Verificamos si el resultado es un comando de interrupción
    if isinstance(result, Command) and result.name == "interrupt":
        query = result.data.get("query", "No query provided.")
        print("\n=== INTERRUPCIÓN HUMANA REQUERIDA ===")
        print(f"Consulta del modelo: {query}")
        human_input = input("Tu respuesta como humano (JSON): ")

        # Resumimos la ejecución con el input humano
        resumed_result = graph.resume(result, {"data": human_input}, config=config)

        if isinstance(resumed_result, dict) and "messages" in resumed_result:
            last_message = resumed_result["messages"][-1]
            content = last_message.content
            content = get_json_content(content)
            return {
                "content": content.get("reply", "No reply provided."),
                "intent": content.get("intent", "No intent provided.")
            }

    # Resultado normal con mensajes
    if isinstance(result, dict) and "messages" in result:
        last_message = result["messages"][-1]
        content = last_message.content
        try:
            content = get_json_content(content)
            return {
                "content": content.get("reply", "No reply provided."),
                "intent": content.get("intent", "No intent provided.")
            }
        except Exception as e:
            print("An error occurred:", e)
    return {
        "content": "No reply provided.",
        "intent": "No intent provided."
    }

def get_json_content(content: str) -> dict:
    match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    if match:
        content_clean = match.group(1)
    else:
        content_clean = content.strip()
    return json.loads(content_clean)