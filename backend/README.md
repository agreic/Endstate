# Endstate Backend

Modular backend for the Endstate knowledge-graph powered learning platform.

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
│   ├── provider.py       # LLM providers (Ollama, Gemini)
│   └── graph_transformer.py  # Text to graph conversion
├── schemas/              # Graph schemas
│   ├── __init__.py
│   ├── base.py           # Base schema class
│   └── skill_graph.py    # Skill dependency schemas
├── services/             # Service layer
│   ├── __init__.py
│   ├── chat_service.py   # Chat with SSE real-time updates
│   └── knowledge_graph.py  # High-level KG service
└── main.py               # FastAPI application
```

## Chat Service (`services/chat_service.py`)

The chat service provides persistent conversations with real-time SSE updates.

### Quick Start

```python
from backend.services.chat_service import chat_service

# Send a message (idempotent via request_id)
response = await chat_service.send_message(
    session_id="user-123",
    content="I want to learn Python",
    request_id="unique-request-id"  # For idempotency
)
# Response: ChatResponse(success=True, content="...", is_processing=False)

# Get all messages
messages = chat_service.get_messages("user-123")
# Returns: [{"role": "user", "content": "...", "timestamp": "...", "request_id": "..."}]

# Check if session is locked (processing)
is_locked = chat_service.is_locked("user-123")

# Reset session (cancels any ongoing processing)
chat_service.delete_session("user-123")
chat_service.create_session("user-123")
```

### Key Classes

**ChatService:**
- `send_message(session_id, content, request_id)` - Send message, returns `ChatResponse`
- `get_messages(session_id)` - Get all messages with timestamps
- `is_locked(session_id)` - Check if processing
- `event_stream(session_id)` - Generate SSE events

**BackgroundTaskStore:**
- Stores running background tasks (like async summary extraction)
- `store(session_id, task)` - Store a task
- `cancel(session_id)` - Cancel a task
- `notify(session_id, event, data)` - Notify subscribers via SSE

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/{id}/messages` | POST | Send message (idempotent) |
| `/api/chat/{id}/stream` | GET | SSE event stream |
| `/api/chat/{id}/messages` | GET | Get all messages |
| `/api/chat/{id}/reset` | POST | Reset and cancel processing |
| `/api/chat/{id}/locked` | GET | Check lock status |
| `/api/projects/{id}/start` | POST | Reinitialize project asynchronously |

### SSE Events

The `/api/chat/{id}/stream` endpoint emits:

- `initial_messages` - Initial message history and lock status
- `message_added` - New message added
- `processing_started` - Started async processing
- `processing_complete` - Finished async processing
- `processing_cancelled` - Processing was cancelled (reset)
- `session_reset` - Session was reset

### Project Acceptance & Summary Extraction

When user accepts a project proposal:
1. Session is locked (prevents new messages)
2. "Creating project plan..." message added
3. Background task extracts summary via LLM
4. Completion message added with project plan
5. Session unlocked

The `X-Request-ID` header ensures idempotency - duplicate requests are detected and ignored.

## Quick Start

```python
from backend import KnowledgeGraphService

# Initialize (uses Gemini by default)
service = KnowledgeGraphService()

# Or use local Ollama
service = KnowledgeGraphService(llm_provider="ollama")

# Extract and add to graph
await service.aextract_and_add('''
    Python requires understanding variables.
    Functions require understanding variables and control flow.
''')

# Query the graph
service.query("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 10")

# Get statistics
print(service.get_stats())

# Clean the graph
service.clean()

# Merge duplicate nodes
service.merge_duplicates("Skill")  # Only Skill, Concept, Topic
```

## Configuration

### Environment Variables

Create a `.env` file (see `.env.example`):

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

## Project Nodes

Project summaries have matching `Project` KG nodes that connect to:
- Project-owned KG nodes via `HAS_NODE`
- Lessons and assessments via `HAS_LESSON` / `HAS_ASSESSMENT`
- A `UserProfile` node via `HAS_PROFILE`

The default "All" project exists for unassigned lessons and is not rendered in the KG.

### Custom Schemas

```python
from backend.schemas.base import GraphSchema

# Define custom schema
MySchema = GraphSchema(
    name="My Custom Schema",
    description="Custom schema for my use case",
    allowed_nodes=["Entity1", "Entity2"],
    allowed_relationships=[
        ("Entity1", "RELATES_TO", "Entity2"),
    ],
    node_properties=["name", "description"],
    relationship_properties=["weight"],
    strict_mode=True,
)

# Use with service
service = KnowledgeGraphService(schema=MySchema)
```

## API Reference

### KnowledgeGraphService

Main service class combining LLM and database operations.

**Extraction:**
- `extract(text)` - Extract graph from text (sync)
- `aextract(text)` - Extract graph from text (async)
- `extract_and_add(text)` - Extract and add to DB (sync)
- `aextract_and_add(text)` - Extract and add to DB (async)

**Graph Management:**
- `clean()` - Delete all nodes and relationships
- `clean_by_label(label)` - Delete nodes with specific label
- `merge_duplicates(label)` - Merge duplicate nodes
- `merge_all_duplicates()` - Merge all duplicates

**Queries:**
- `query(cypher, params)` - Execute Cypher query
- `get_stats()` - Get graph statistics
- `get_nodes(label, limit)` - Get nodes

## API Endpoints (FastAPI)

### Graph

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph` | GET | Graph nodes + relationships (Skill, Concept, Topic, Project) |
| `/api/graph/stats` | GET | Graph stats (filtered to KG entities) |
| `/api/graph/node/{id}/connections` | GET | Connected nodes for a node |
| `/api/graph/nodes/{id}` | DELETE | Delete a node |
| `/api/graph/relationships` | DELETE | Delete a relationship |
| `/api/merge` | POST | Merge duplicates (Skill/Concept/Topic only) |

### Projects

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects` | GET | List project summaries |
| `/api/projects/{id}` | GET | Project details |
| `/api/projects/{id}/name` | PATCH | Rename project |
| `/api/projects/{id}/profile` | PATCH | Update user profile |
| `/api/projects/{id}` | DELETE | Delete project (default project clears content) |
| `/api/projects/{id}/chat` | GET | Project chat history |
| `/api/projects/{id}/start` | POST | Reinitialize project (async job) |

### Lessons & Assessments

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects/{id}/lessons` | GET | List lessons |
| `/api/projects/{id}/lessons/generate` | POST | Generate lesson for node in project |
| `/api/projects/{id}/lessons/{lesson_id}/archive` | POST | Archive lesson |
| `/api/projects/{id}/lessons/{lesson_id}` | DELETE | Delete lesson |
| `/api/graph/nodes/{node_id}/lesson` | POST | Generate lesson for node (single project) |
| `/api/graph/nodes/{node_id}/lessons/generate` | POST | Generate lessons for all connected projects |
| `/api/projects/{id}/assessments` | GET | List assessments |
| `/api/projects/{id}/assessments` | POST | Generate assessment (async job) |
| `/api/projects/{id}/assessments/{assessment_id}/submit` | POST | Submit assessment |
| `/api/projects/{id}/assessments/{assessment_id}/archive` | POST | Archive assessment |
| `/api/projects/{id}/assessments/{assessment_id}` | DELETE | Delete assessment |

### Jobs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs/{job_id}` | GET | Get async job status |
| `/api/jobs/{job_id}` | DELETE | Cancel async job |
- `get_relationships(limit)` - Get relationships
- `visualize()` - Get visualization data

### Neo4jClient

Low-level database operations.

### GraphTransformer

LLM-based text to graph transformation.

## Predefined Schemas

- `SkillGraphSchema` - Full schema for learning paths (default)
- `MinimalSkillSchema` - Simplified skill dependencies
- `ContentExtractionSchema` - Extract from educational content

## Running Examples

```bash
# With Gemini
python -m backend.examples.basic_usage

# With Ollama
LLM_PROVIDER=ollama python -m backend.examples.basic_usage
```

## Dependencies

- `langchain-neo4j` - LangChain Neo4j integration
- `langchain-experimental` - Graph transformers
- `langchain-ollama` - Ollama LLM support
- `langchain-google-genai` - Gemini LLM support
- `neo4j` - Neo4j Python driver
- `neo4j-viz` - Graph visualization (optional)
