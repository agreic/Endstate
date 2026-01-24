# Endstate

Knowledge-graph powered learning platform with AI-guided project creation and iterative skill assessment.

## The Endstate Loop

```
Goal → Chat (Interviewer) → Suggest Projects → Project → KG → Lessons → Assessments → Capstone → Evaluation → Complete
```

## Key Features

### 1. Conversational Project Discovery
- Chat with the Socratic interviewer to clarify goals
- Click “Suggest Projects” to generate 3 concrete options
- Select a proposal card to create a project (no “I accept” typing)

### 2. Skill-Graph Learning Path
- Visual knowledge graph of skills and concepts
- Dependencies between skills shown
- Lessons and assessments linked to projects

### 3. Iterative Capstone Evaluation
- Text-based submissions (flexible, LLM-evaluatable)
- Rubric-based LLM evaluation with skill-to-evidence mapping
- Constructive feedback for improvement
- Unlimited resubmissions until complete

### 4. Persistent Chat Archive
- All conversations saved alongside projects
- Projects tab shows chat history per project
- Review learning journey anytime

## Architecture

```
endstate/
├── frontend/           # Vue 3 + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── components/ # Vue components
│   │   │   ├── ChatBox.vue        # Chat UI
│   │   │   ├── KnowledgeGraph.vue # Graph visualization
│   │   │   ├── Projects.vue       # Project management
│   │   │   ├── CapstoneSubmission.vue  # Submission UI
│   │   │   └── EvaluationResult.vue    # Feedback display
│   │   ├── composables/  # Vue composables
│   │   │   └── useChat.ts # Chat state + SSE
│   │   └── services/     # API client
│   │       └── api.ts
│   └── dist/
├── backend/            # Python FastAPI
│   ├── services/
│   │   ├── chat_service.py      # Chat + SSE + background tasks
│   │   ├── evaluation_service.py # Rubric-based evaluator
│   │   └── summary_cache.py      # Project + chat storage
│   ├── db/
│   │   └── neo4j_client.py       # Neo4j operations
│   ├── llm/
│   │   └── provider.py           # Ollama/Gemini
│   └── main.py                   # FastAPI app
└── tests/
```

## Chat System

- Real-time updates via Server-Sent Events (SSE)
- Idempotent message sending prevents duplicates
- Project suggestions are requested explicitly and returned as cards
- Chat history stored in Neo4j alongside the project

## Knowledge Graph

- Skills, concepts, topics as nodes
- Dependencies shown as relationships
- Projects connected to relevant skills
- Chat sessions stored separately from graph data

## Capstone Evaluation

- Submit a text solution explaining skill application
- LLM evaluates against rubric (skill application, understanding, completeness)
- Feedback delivered with suggestions for improvement
- Resubmit and iterate until complete (score ≥ 0.7 + all skills evidenced)

## Installation

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install
```

## Running the Application

### Development Mode (Recommended)

```bash
# Terminal 1: Start backend with hot reload
uv run uvicorn backend.main:app --reload

# Terminal 2: Start frontend dev server
cd frontend && npm run dev
```

Access at http://localhost:3000

### Docker (Production)

```bash
docker compose up -d --build --force-recreate
```

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

## Dependencies

### Core
- Python 3.11+
- Vue 3 + TypeScript
- Neo4j database
- LLM (Ollama or Gemini)

### See `pyproject.toml` and `frontend/package.json` for full dependency lists.
