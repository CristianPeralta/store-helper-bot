# Store Helper Bot

A conversational assistant built with **FastAPI**, **LangChain**, and **PostgreSQL**, designed to help users quickly get information about store products, availability, prices, and general store details like hours or location.

## Features

- **Chatbot with Memory**  
  Remembers users and their previous interactions to deliver a more personalized experience.

- **Tool Integration**  
  Uses the [FakeStoreAPI](https://fakestoreapi.com/) to answer questions about stock, prices, and products.

- **Custom Chat State**  
  Switches between different modes such as consultation or escalation to a human.

- **Human-in-the-loop**  
  When needed, the bot will escalate the conversation to a human operator.

- **Data Persistence**  
  Tracks users, conversations, states, and messages in a structured PostgreSQL database.

## Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/)
- **AI/ML**: [LangChain](https://www.langchain.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/)
- **External API**: [FakeStoreAPI](https://fakestoreapi.com/)
- **Testing**: pytest, pytest-asyncio, pytest-cov

## Project Structure

```
store-helper-bot/
├── alembic/                 # Database migrations
├── app/                     # Application code
│   ├── core/                # Core functionality (config, logging, etc.)
│   ├── db/                  # Database models and session management
│   ├── langchain/           # LangChain setup and tools
│   ├── routes/              # API endpoints
│   ├── schemas/             # Pydantic models
│   ├── services/            # Business logic
│   └── main.py              # FastAPI application entry point
├── tests/                   # Test suite
│   ├── e2e/                 # End-to-end tests
│   ├── integration/         # Integration tests
│   └── unit/                # Unit tests
├── .env.example             # Example environment variables
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 13+
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/CristianPeralta/store-helper-bot.git
   cd store-helper-bot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Environment Variables

Create a `.env` file in the root directory with the following variables. Copy the contents from `.env.example` and update the values as needed.

> **Important**: You must obtain a `FIREWORKS_API_KEY` from [Fireworks AI](https://fireworks.ai/) to use the chatbot features with Fireworks models. This key is required for the AI functionality to work properly.

### Using Local Models with Ollama

The application supports using local models through [Ollama](https://ollama.ai/). To use a local model:

1. Install and run Ollama on your machine:
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Start the Ollama server
   ollama serve &
   
   # Pull a model (example using Qwen 7B)
   ollama pull qwen:7b
   ```

2. Configure your `.env` file to use the local model:
   ```
   # In your .env file
   MODEL_PROVIDER=openai
   # The following values are required but not used when using Ollama locally
   FIREWORKS_API_KEY=not-needed
   ```

3. The application will automatically connect to your local Ollama server at `http://localhost:11434`

> **Note**: When using local models, make sure you have sufficient system resources (RAM and CPU/GPU) to run the model efficiently.

```
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/store_helper

# LangChain
OPENAI_API_KEY=your_openai_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langchain_api_key

# Application
DEBUG=true
```

### Database Setup

1. Create a PostgreSQL database:
   ```sql
   CREATE DATABASE store_helper;
   ```

2. Run migrations:
   ```bash
   alembic upgrade head
   ```

## Running the Application

### Web Server
Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Console Interface
You can also interact with the chatbot directly from the command line using the console interface:

```bash
python -m app.cli.chat
```

This will start an interactive chat session where you can:
- Type your messages and get responses from the assistant
- See the conversation history
- The chat session will be persisted in the database

Example usage:
```
$ python -m app.cli.chat
Starting Store Helper Bot console interface...
Type 'exit' or 'quit' to end the session.

You: Do you have any backpacks in stock?
Assistant: Yes, we have several backpacks available...
```

## API Documentation

Once the application is running, you can access:

- **Interactive API docs**: `http://localhost:8000/docs`
- **Alternative API docs**: `http://localhost:8000/redoc`

## Example Queries

- "Do you have any backpacks in stock?"
- "How much does the red t-shirt cost?"
- "Where is the store located?"
- "I need to talk to someone."

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app

# Run specific test file
pytest tests/unit/test_example.py

# Run tests with detailed output
pytest -v
```

## Project Architecture

### Conversation Flow

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

### LangGraph State Machine

This project leverages **LangGraph** to manage conversation flows through a state machine pattern. The graph-based approach allows for more flexible and maintainable conversation handling, especially for complex multi-turn interactions.

<p align="center">
  <img src="docs/diagrams/workflow.png" alt="LangGraph State Machine" />
</p>

The diagram illustrates our conversation flow, where:
- **Nodes** represent different states or actions in the conversation
- **Edges** define the possible transitions between states
- **Conditional logic** determines the flow based on user input and conversation context

## Dependencies

### Main Dependencies
- FastAPI
- LangChain
- SQLAlchemy
- PostgreSQL
- Pydantic
- httpx

### Development Dependencies
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock
- factory-boy

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*This project is actively maintained. For support, please open an issue in the repository.*