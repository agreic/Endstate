# Endstate Backend

FastAPI backend for the Endstate knowledge-graph powered learning platform.

## Structure

```
backend/
├── __init__.py           # Main exports
├── config.py             # Configuration management
├── db/                   # Database layer
│   ├── __init__.py
│   └── neo4j_client.py   # Neo4j operations
├── llm/                  # LLM layer
│   ├── __init__.py
│   └── provider.py       # LLM providers (Ollama, Gemini)
├── services/             # Service layer
│   ├── __init__.py
│   ├── chat_service.py   # Chat with SSE real-time updates
│   ├── evaluation_service.py  # Rubric-based capstone evaluator
│   └── lesson_service.py # Lesson generation
└── main.py               # FastAPI application
```

## Services

### Chat Service

Handles persistent chat conversations with real-time SSE updates.

**Key Features:**
- Idempotent message sending via `X-Request-ID` header
- Processing state prevents concurrent requests
- Background task management for async operations
- Explicit project suggestions via `/api/suggest-projects`

**SSE Events:**
- `initial_messages` - Message history and status
- `message_added` - New message delivered
- `processing_started/complete` - Async operation status
- `error` - Error messages for display
- `heartbeat` - Keep-alive (silent)

### Evaluation Service

Rubric-based capstone evaluation using the same LLM as chat.

**Rubric:**
- Skill Application (50%) - Correct application of required skills
- Conceptual Understanding (30%) - Understanding demonstrated
- Completeness (20%) - Addresses full project brief

**Completion Criteria:**
- Score ≥ 0.7 AND all required skills evidenced

### Summary Cache
Project summaries and chat history are stored in Neo4j.

## API Endpoints

### Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/{id}/stream` | GET | SSE event stream |
| `/api/chat/{id}/messages` | POST | Send message |
| `/api/chat/{id}/messages` | GET | Get message history |
| `/api/chat/{id}/reset` | POST | Reset session |
| `/api/suggest-projects` | POST | Generate project options from chat history |
| `/api/suggest-projects/accept` | POST | Accept a project option |

### Knowledge Graph

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph` | GET | Graph nodes + relationships |
| `/api/graph/stats` | GET | Graph statistics |

### Projects

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects` | GET | List projects |
| `/api/projects/{id}` | GET | Project details |
| `/api/projects/{id}/submit` | POST | Submit capstone |
| `/api/projects/{id}/submissions` | GET | Submission history |

## Configuration

Create a `.env` file:

```bash
# LLM Provider
LLM_PROVIDER=gemini  # or "ollama"

# Gemini API
GOOGLE_API_KEY=your_api_key

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
```

## Quick Start

```bash
# Run the API server
uv run uvicorn backend.main:app --reload

# API docs at http://localhost:8000/docs
```
