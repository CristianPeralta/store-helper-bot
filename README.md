<div align="center">
  <h1>Store Helper Bot</h1>
  <p>A conversational assistant for store information and product queries</p>
  
  
  [![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![LangChain](https://img.shields.io/badge/LangChain-FF6B00?style=flat)](https://www.langchain.com/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

  <div>
    <img src="./docs/cli-example.gif" alt="CLI Demo" width="800">
  </div>
  
</div>

## 🚀 Quick Start

Get up and running in minutes:

```bash
# Clone and setup
$ git clone https://github.com/CristianPeralta/store-helper-bot.git
$ cd store-helper-bot

# Install dependencies
$ python -m venv venv
$ source venv/bin/activate  # On Windows: venv\Scripts\activate
$ pip install -r requirements.txt

# Run the CLI interface
$ python -m app.cli.chat
```

## 🌟 API Interface

In addition to the CLI shown above, the application also provides a REST API for integration with other applications:

```bash
# Start the API server
uvicorn app.main:app --reload
```

Access the interactive API documentation at `http://localhost:8000/docs` for a complete reference and to test the endpoints directly from your browser.

<div align="center">
  <img src="./docs/api-example.gif" alt="API Demo" width="700">
</div>

## ✨ Features

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

## 🛠️ Tech Stack

<div align="center">
  <table>
    <tr>
      <td align="center"><b>Backend</b></td>
      <td align="center"><b>AI/ML</b></td>
      <td align="center"><b>Database</b></td>
      <td align="center"><b>Tools</b></td>
    </tr>
    <tr>
      <td>
        <a href="https://fastapi.tiangolo.com/">
          <img src="https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png" width="100" alt="FastAPI">
        </a>
      </td>
      <td>
        <a href="https://www.langchain.com/">
          <img src="https://opensource.muenchen.de/logo/langchain.jpg" width="100" alt="LangChain">
        </a>
      </td>
      <td>
        <a href="https://www.postgresql.org/">
          <img src="https://www.postgresql.org/media/img/about/press/elephant.png" width="100" alt="PostgreSQL">
        </a>
      </td>
      <td>
        <a href="https://www.sqlalchemy.org/">
          <img src="https://upload.wikimedia.org/wikipedia/commons/d/d7/SQLAlchemy.svg" width="100" alt="SQLAlchemy">
        </a>
      </td>
    </tr>
  </table>
</div>

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

## 💬 Console Interface

Interact with the chatbot directly from your terminal:

```bash
python -m app.cli.chat
```

### Features
- Natural language processing for product queries
- Persistent conversation history
- Context-aware responses
- Easy integration with store databases

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