# Store Helper Bot

A conversational assistant built with **FastAPI**, **LangChain**, and **PostgreSQL**, designed to help users quickly get information about store products, availability, prices, and general store details like hours or location.

---

## Features

- **Chatbot with memory**  
  Remembers users and their previous interactions to deliver a more personalized experience.

- **Tool integration**  
  Uses the [FakeStoreAPI](https://fakestoreapi.com/) to answer questions about stock, prices, and products.

- **Custom chat state**  
  Switches between different modes such as consultation, or escalation to a human.

- **Human-in-the-loop**  
  When needed, the bot will escalate the conversation to a human operator.

- **Data persistence with PostgreSQL**  
  Tracks users, conversations, states, and messages in a structured way.

---

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/)
- [LangChain](https://www.langchain.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [FakeStoreAPI](https://fakestoreapi.com/)

---

## Project Structure

```bash
store-helper-bot/
├── app/
│ ├── main.py # FastAPI app entry point
│ ├── routes/ # Chat and tool endpoints
│ ├── langchain/ # LangChain setup, tools, memory
│ ├── db/ # Models and database logic
│ └── core/ # Config, utils, etc.
├── tests/ # Unit and integration tests
├── README.md
├── requirements.txt
└── .env
```

## Flowchart

```mermaid
flowchart TD
    A["Start: Client sends message"] --> B["Create anonymous session"]
    B --> C["Analyze intent with LLM"]
    C --> C1{"Was intent detected?"}
    
    C1 -- No --> O["Respond 'not understood' and offer human operator"]
    O --> P{"Does client want to talk to an operator?"}
    P -- Yes --> Q["Request email and name, then transfer to human"] --> I
    P -- No --> R["Offer additional help"] --> I

    C1 -- Yes --> D{"Type of intent?"}
    D -- Product inquiry --> F["Enter inquiry mode"] --> E["Search in FakeStoreAPI"]
    D -- General question --> G["Search info in local database"]
    D -- Other --> R

    E --> I
    G --> I

    I["Respond to client"] --> L["Log interaction in PostgreSQL"]
    L --> M{"Does client need to continue?"}
    M -- Yes --> C
    M -- No --> N["End: Show session number (for tracking)"]
```
---

## LangGraph State Machine

This project leverages **LangGraph** to manage conversation flows through a state machine pattern. The graph-based approach allows for more flexible and maintainable conversation handling, especially for complex multi-turn interactions.

<p align="center">
  <img src="langgraph_diagrama.png" alt="LangGraph State Machine" />
</p>

The diagram above illustrates our conversation flow, where:
- **Nodes** represent different states or actions in the conversation
- **Edges** define the possible transitions between states
- **Conditional logic** determines the flow based on user input and conversation context

This architecture provides several benefits:
- Clear visualization of conversation flows
- Easy modification and extension of conversation paths
- Better handling of complex, branching conversations
- Improved maintainability and debugging

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/CristianPeralta/store-helper-bot.git
cd store-helper-bot
```

---
### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---
### 3. Setup environment

Create a .env file with the following variables:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/store_bot
```

---
### 4. Run the app

```bash
python run.py
```

---

### Example Queries

- “Do you have any backpacks in stock?”
- “How much does the red t-shirt cost?”
- “Where is the store located?”
- “I need to talk to someone.”

---
### License
MIT License. Feel free to fork and build upon it.