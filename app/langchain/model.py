import os
from langchain.chat_models import init_chat_model

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

def stream_graph_updates(user_input: str):
    events = graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config,
        stream_mode="values",
    )

    for event in events:
        if isinstance(event, Command) and event.name == "interrupt":
            query = event.data.get("query", "No query provided.")
            print("\n=== INTERRUPCIÓN HUMANA REQUERIDA ===")
            print(f"Consulta del modelo: {query}")
            human_input = input("Tu respuesta como humano (JSON): ")

            try:
                human_data = json.loads(human_input)
            except json.JSONDecodeError:
                print("Entrada inválida. Debe ser un JSON válido.")
                return

            events = graph.resume(event, {"data": human_data}, config=config)

            for resumed_event in events:
                if "messages" in resumed_event:
                    resumed_event["messages"][-1].pretty_print()

        elif "messages" in event:
            event["messages"][-1].pretty_print()