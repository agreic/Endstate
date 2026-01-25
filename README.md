# Endstate

Knowledge-graph powered learning platform with AI-guided project creation and iterative skill assessment.

## The Endstate Loop

```
Goal → Chat (Interviewer) → Suggest Projects → Project → KG → Lessons → Assessments → Capstone → Complete
```

## Key Features

### 1. Conversational Project Discovery
- Socratic interviewer clarifies goals through chat
- "Suggest Projects" generates 3 concrete options
- Select a proposal card to create a project

### 2. Skill-Graph Learning Path
- Visual knowledge graph of skills and concepts
- Dependencies between skills explicitly shown
- Lessons and assessments linked to projects

### 3. Iterative Capstone Evaluation
- Text-based submissions (flexible, LLM-evaluatable)
- Rubric-based evaluation with skill-to-evidence mapping
- Constructive feedback with unlimited resubmissions

### 4. Persistent Chat Archive
- All conversations saved alongside projects
- Review learning journey anytime

## Architecture

```
endstate/
├── frontend/           # Vue 3 + TypeScript + Tailwind CSS
│   ├── src/components/ # ChatBox, KnowledgeGraph, Projects, etc.
│   ├── src/composables/# useChat (SSE state management)
│   └── src/services/   # API client
├── backend/            # Python FastAPI
│   ├── services/       # chat, evaluation, lesson, knowledge_graph
│   ├── db/             # neo4j_client
│   ├── llm/            # provider (Ollama/Gemini)
│   └── main.py         # FastAPI app
└── tests/
```

## Chat System

- Real-time updates via Server-Sent Events (SSE)
- Idempotent message sending prevents duplicates
- Project suggestions requested explicitly via "Suggest Projects"
- Chat history stored in Neo4j alongside projects

## Knowledge Graph

- Skills, concepts, topics as nodes
- Dependencies shown as relationships
- Projects connected to relevant skills
- Chat sessions stored separately from graph data

## Capstone Evaluation

- Submit text solution explaining skill application
- LLM evaluates against rubric (skill application, understanding, completeness)
- Feedback with suggestions for improvement
- Resubmit until complete (score ≥ 0.7 + all skills evidenced)

## Installation

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install
```

## Running

### Development Mode

```bash
# Terminal 1: Backend with hot reload
uv run uvicorn backend.main:app --reload

# Terminal 2: Frontend dev server
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

## Dependencies

- Python 3.11+
- Vue 3 + TypeScript
- Neo4j database
- LLM (Ollama or Gemini)

See `pyproject.toml` and `frontend/package.json` for full dependency lists.
