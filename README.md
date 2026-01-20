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

The chat system provides persistent, real-time conversations with the following architecture:

**Backend (`backend/services/chat_service.py`):**
- `ChatService` - Main service for chat operations
- `BackgroundTaskStore` - Manages background tasks (like async summary extraction) with cancellation support
- `send_message()` - Idempotent message sending via `X-Request-ID` header
- `event_stream()` - SSE endpoint for real-time updates
- Automatic project summary extraction after user accepts a project proposal

**Frontend (`frontend/src/composables/useChat.ts`):**
- `useChat()` - Composable for chat state management
- SSE event stream connection with automatic reconnection
- Single `status` state: `idle` | `loading` | `processing` | `error`
- Backend is source of truth - no local message duplication

**Flow:**
1. User sends message → Frontend calls `POST /api/chat/{id}/messages`
2. Message stored in Neo4j with `request_id` for idempotency
3. Response returned (with `is_processing: true` if project accepted)
4. Frontend shows loading/processing indicator
5. SSE stream updates messages in real-time
6. Reset button cancels ongoing processing and clears session

**Endpoints:**
- `POST /api/chat/{id}/messages` - Send message (idempotent)
- `GET /api/chat/{id}/stream` - SSE event stream
- `GET /api/chat/{id}/messages` - Get all messages
- `POST /api/chat/{id}/reset` - Reset session (cancels processing)

### Knowledge Graph

See [[backend/README.md]] for detailed knowledge graph documentation.

## Installation

```bash
# Install dependencies
uv sync

# Add optional development dependencies
uv add --dev pytest pytest-asyncio
```

## Development

### Frontend (Vue 3 + TypeScript + Tailwind)

```bash
cd frontend

# Development server
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

# Run Python development
uv run python
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
