![Logo](Logo.png)

# Endstate

Knowledge-graph powered learning platform with interactive AI agents.

## Overview

Endstate is an intelligent learning architect that transforms vague personal goals into executable, visual skill maps and concrete capstone projects. Instead of generic advice, it dynamically generates personalized micro-lessons and adapts your roadmap in real-time based on your actual performance.

For more info, see the [[IDEA.md]] file.

## Architecture

```
endstate/
├── frontend/           # Vue 3 + TypeScript + Tailwind CSS
│   ├── src/           # Source code
│   │   ├── components/# Vue components (ChatBox.vue, etc.)
│   │   ├── composables/# Vue composables (useChat.ts)
│   │   └── services/  # API client (api.ts)
│   ├── public/        # Static assets
│   └── dist/          # Build output
├── backend/            # Python FastAPI backend
│   ├── services/      # Service layer (chat_service.py, knowledge_graph.py)
│   ├── db/            # Database layer (neo4j_client.py)
│   └── main.py        # FastAPI application
└── tests/             # Test files
```

## Key Features

### Chat System

The chat system provides persistent conversations with AI that can extract and create learning projects.

**Backend (`backend/services/chat_service.py`):**
- `ChatService` - Main service for chat operations
- `BackgroundTaskStore` - Manages background tasks (like async summary extraction) with cancellation support
- Idempotent message sending via `X-Request-ID` header prevents duplicate messages
- Automatic project summary extraction after user accepts a project proposal

**Frontend (`frontend/src/composables/useChat.ts`):**
- `useChat()` - Composable for chat state management
- Session persistence via `localStorage` (key: `endstate_chat_session_id`)
- Messages reload when navigating back to chat tab
- Processing state shows when background extraction is running

**Flow:**
1. User sends message → Frontend calls `POST /api/chat/{id}/messages`
2. Message stored in Neo4j with `request_id` for idempotency
3. Response returned (with `is_processing: true` if project accepted)
4. Frontend shows processing indicator during async extraction
5. Reset button cancels ongoing processing and clears session

**Endpoints:**
- `POST /api/chat/{id}/messages` - Send message (idempotent)
- `GET /api/chat/{id}/messages` - Get all messages
- `POST /api/chat/{id}/reset` - Reset session (cancels processing)

### Knowledge Graph

The knowledge graph stores learned concepts, skills, and their relationships.

**Data Isolation:**
- Chat sessions and messages are stored separately from knowledge graph data
- Graph statistics exclude `ChatSession` and `ChatMessage` nodes
- `/api/graph` endpoints only return knowledge graph entities

**Methods:**
- `get_knowledge_graph_nodes()` - Get nodes excluding chat-related labels
- `get_knowledge_graph_relationships()` - Get relationships excluding chat relationships
- `get_knowledge_graph_stats()` - Get statistics for knowledge graph only

See [[backend/README.md]] for detailed knowledge graph documentation.

## Installation

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install
```

## Running the Application

### Development Mode (Recommended)

Run backend and frontend separately for hot reloading:

```bash
# Terminal 1: Start backend with hot reload
cd /path/to/endstate
uv run uvicorn backend.main:app --reload

# Terminal 2: Start frontend dev server
cd /path/to/endstate/frontend
npm run dev
```

Access the application at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Docker (Production)

Build and run the full stack with Docker Compose:

```bash
# Build and start all services
docker compose up -d --build --force-recreate

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

Access the application at http://localhost:3000

## Development

### Frontend (Vue 3 + TypeScript + Tailwind)

```bash
cd frontend

# Development server with hot reload
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

### Backend

```bash
# Run tests
uv run pytest

# Run Python REPL
uv run python

# Lint code
uv run ruff check .
```

## Testing

```bash
# Run all tests
uv run pytest

# Frontend tests
cd frontend && npm test
```

## Dependencies

### Core Dependencies
- Python 3.11+

### Development Dependencies
- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support

### Frontend Dependencies
- Vue 3 + TypeScript
- Tailwind CSS
- Vite build tool

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Add your license information here]
