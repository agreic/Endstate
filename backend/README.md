# Endstate Backend

FastAPI backend for the Endstate knowledge-graph powered learning platform.

## Structure

```
backend/
├── config.py             # Configuration management
├── db/
│   └── neo4j_client.py   # Neo4j operations
├── llm/
│   └── provider.py       # LLM providers (Ollama, Gemini)
├── services/
│   ├── chat_service.py       # Chat with SSE real-time updates
│   ├── evaluation_service.py # Rubric-based capstone evaluator
│   ├── lesson_service.py     # Lesson generation
│   ├── knowledge_graph.py    # Graph extraction and management
│   └── assessment_service.py # Assessment generation
└── main.py               # FastAPI application
```

## Services

### Chat Service
- Persistent chat conversations with real-time SSE updates
- Idempotent message sending via `X-Request-ID` header
- Background task management for async operations
- Explicit project suggestions via `/api/suggest-projects`

**SSE Events**: `initial_messages`, `message_added`, `processing_started/complete`, `error`, `heartbeat`

### Evaluation Service
Rubric-based capstone evaluation using the configured LLM.

**Rubric**:
- Skill Application (50%)
- Conceptual Understanding (30%)
- Completeness (20%)

**Completion**: Score ≥ 0.7 AND all required skills evidenced

### Lesson Service
Generates focused lessons for knowledge graph nodes, personalized to user profile.

### Knowledge Graph Service
Extracts skills, concepts, and topics from text using LLM-powered graph generation.

## API Endpoints

### Chat
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/{id}/stream` | GET | SSE event stream |
| `/api/chat/{id}/messages` | POST | Send message |
| `/api/chat/{id}/messages` | GET | Get message history |
| `/api/chat/{id}/reset` | POST | Reset session |
| `/api/suggest-projects` | POST | Generate project options |
| `/api/suggest-projects/accept` | POST | Accept a project |

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
