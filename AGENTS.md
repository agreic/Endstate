# AGENTS.md - Endstate Development Guide

> ← Back to [Main README](./README.md)

Quick reference for agentic coding agents working on Endstate.

## Build & Run Commands

### Frontend (Vue 3 + TypeScript + Tailwind)

```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Development server
npm run build        # Production build
npm run typecheck    # Type checking
```

### Python Backend

```bash
uv sync              # Install dependencies
uv add <package>     # Add dependency
uv run uvicorn backend.main:app --reload  # Run server
```

### Testing

```bash
# Frontend
cd frontend && npm test

# Python
uv run pytest
uv run pytest tests/test_file.py              # Single file
uv run pytest --cov=backend --cov-report=term # With coverage
```

## Code Style

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Python modules | snake_case | `knowledge_graph.py` |
| TypeScript files | kebab-case | `knowledge-graph.ts` |
| Vue components | PascalCase | `KnowledgeGraph.vue` |
| Classes | PascalCase | `GraphDatabase` |
| Functions/methods | snake_case | `build_index()` |
| Variables | snake_case | `node_count` |
| Constants | UPPER_SNAKE_CASE | `MAX_DEPTH` |
| CSS classes | kebab-case | `bg-surface-100` |

### Python
- Use type hints
- Prefer `Optional[T]` over `T | None`
- Explicit exception types, never bare `except:`
- Early returns over nested if-else

### TypeScript/Vue
- Composition API with `<script setup>`
- Use `ref()` for primitives, `reactive()` for objects
- Define props with TypeScript interfaces
- Explicit types over `any`

### Tailwind CSS
- Semantic color names: `text-surface-600`, `bg-primary-500`
- Group classes: layout → spacing → typography → colors

## Git Workflow

### Files to Commit
```
✅ Source code (*.py, *.vue, *.ts)
✅ Config (pyproject.toml, package.json, tsconfig.json)
✅ Lockfiles (uv.lock, package-lock.json)
✅ Tests
✅ Documentation (*.md)

❌ Build output (dist/, __pycache__/, *.pyc)
❌ Dependencies (node_modules/, .venv/)
❌ Environment files (.env, *.local)
❌ IDE configs (.vscode/, .idea/)
```

### Commit Message Format
```
<type>(<scope>): <subject>

feat(chat): add typing indicator
fix(graph): resolve D3 zoom regression
docs(readme): update installation steps
```

**Types**: feat, fix, docs, style, refactor, test, chore

### Before Committing
1. Run linter: `uv run ruff check .` or `npm run typecheck`
2. Run tests: `uv run pytest` or `npm test`
3. Review changes: `git diff --staged`

## Security
- Never commit secrets, keys, or credentials
- Use environment variables for sensitive configuration
- Validate and sanitize all user inputs
- Use parameterized queries for database operations

## Project Workflow Notes
- Chat is a Socratic interviewer
- Project creation via explicit "Suggest Projects" button
- LLM providers: Ollama (local), Gemini, or OpenRouter
