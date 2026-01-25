# AGENTS.md - Endstate Development Guide

This file provides guidelines for agentic coding agents working on the Endstate project.

## Build, Lint, and Test Commands

### Frontend (Vue 3 + TypeScript + Tailwind)

```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Python Backend

```bash
# Install dependencies
uv sync

# Add dependency
uv add <package>
uv add --dev <package>

# Remove dependency
uv remove <package>

# Update dependencies
uv sync --upgrade
```

### Testing

```bash
# Frontend tests
cd frontend
npm test              # Run all tests
npm test -- --run     # Run tests once (no watch)

# Python tests
uv run pytest
uv run pytest tests/test_file.py              # Single test file
uv run pytest tests/test_file.py::test_func   # Single test function
uv run pytest --cov=src --cov-report=term-missing  # With coverage
```

## Code Style Guidelines

### General Principles
- Write clean, readable, and maintainable code
- Favor simplicity over cleverness
- Keep functions and modules focused on a single responsibility
- Write self-documenting code with descriptive names

### Imports
- **Python**: stdlib → third-party → local, sorted alphabetically
- **TypeScript/Vue**: Vue → third-party → local, named imports preferred
- Avoid wildcard imports (`from module import *`)

### Types
- **Python**: Use type hints, prefer `Optional[T]` over `T | None`
- **TypeScript**: Explicit types over `Any`, prefer `interface` over `type`
- Name type variables: `T`, `K`, `V`, `R`

### Naming Conventions
| Type | Convention | Examples |
|------|------------|----------|
| Python modules | snake_case | `knowledge_graph.py` |
| TypeScript files | kebab-case | `knowledge-graph.ts` |
| Vue components | PascalCase | `KnowledgeGraph.vue` |
| Classes | PascalCase | `GraphDatabase` |
| Functions/methods | snake_case | `build_index()` |
| Variables | snake_case | `node_count` |
| Constants | UPPER_SNAKE_CASE | `MAX_DEPTH` |
| Component props | camelCase | `isOpen` |
| CSS classes | kebab-case | `bg-surface-100` |

### Error Handling
- Use explicit exception types, never bare `except:`
- Create custom exception classes for domain errors
- Prefer early returns over nested if-else
- Wrap external API calls with specific exception handling

### Vue 3 Specifics
- Use Composition API with `<script setup>`
- Use `ref()` for primitives, `reactive()` for objects
- Define props with TypeScript interfaces
- Emit events with `defineEmits<{ event: [payload] }>()`

### Tailwind CSS
- Use semantic color names: `text-surface-600`, `bg-primary-500`
- Follow spacing scale: `p-4`, `m-2`, `gap-3`
- Group classes: layout → spacing → typography → colors

## Git Workflow

### Commit Principles
- **Atomic commits**: One feature/fix per commit
- **Working state**: Every commit should leave the codebase runnable
- **Traceable**: From any commit, `git checkout` should produce a working codebase

### Files to Commit
```
# Always commit
- Source code (*.py, *.vue, *.ts, *.tsx)
- Configuration (pyproject.toml, package.json, tsconfig.json)
- Package lockfiles (uv.lock, package-lock.json)
- Test files
- AGENTS.md, README.md

# Never commit
- Build output (dist/, build/, __pycache__/, *.pyc)
- Dependencies (node_modules/, .venv/, venv/)
- Environment files (.env, *.local, .env.*)
- IDE configs (.vscode/, .idea/)
- Temporary files (*.tmp, *.swp, *.log)
- OS files (.DS_Store, Thumbs.db)
```

### .gitignore Best Practices

Add these patterns when introducing new technologies:

```gitignore
# === Frontend ===
frontend/node_modules/           # npm dependencies (regenerate with npm install)
frontend/dist/                   # Vite build output
frontend/.vite/                  # Vite cache
*.local                          # Local environment overrides

# === Python ===
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
*.egg-info/

# === General ===
.env
.env.*
!.env.example
*.log
.DS_Store
```

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, style, refactor, test, chore

**Examples**:
```
feat(chat): add typing indicator animation
fix(graph): resolve D3 zoom regression on node click
docs(readme): update installation instructions
```

### Before Committing
1. Run linter: `npm run lint` (frontend) or `uv run ruff check .` (Python)
2. Run tests: `npm test` or `uv run pytest`
3. Verify build: `npm run build` or `uv run build`
4. Review changes: `git diff --staged`

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: New features
- `fix/*`: Bug fixes
- `hotfix/*`: Emergency fixes

## Security
- Never commit secrets, keys, or credentials
- Use environment variables for sensitive configuration
- Validate and sanitize all user inputs
- Use parameterized queries for database operations

## Configuration
- Use environment-specific config files (dev, staging, prod)
- Never hardcode configuration values
- Document all configuration options


