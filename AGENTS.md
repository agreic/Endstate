# AGENTS.md - Endstate Development Guide

This file provides guidelines for agentic coding agents working on the Endstate project.

## Project Structure

```
endstate/
├── frontend/           # Vue 3 + TypeScript + Tailwind CSS
│   ├── src/           # Source code
│   ├── public/        # Static assets
│   └── dist/          # Build output
├── src/               # Python backend (future)
└── tests/             # Test files
```

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

### Testing (when configured)

```bash
# Frontend tests
cd frontend
npm test              # Run all tests
npm test -- --run     # Run tests once (no watch)

# Python tests
uv run pytest
uv run pytest tests/test_file.py
uv run pytest tests/test_file.py::test_function_name
uv run pytest --cov=src --cov-report=term-missing
```

## Code Style Guidelines

### General Principles
- Write clean, readable, and maintainable code
- Favor simplicity over cleverness
- Keep functions and modules focused on a single responsibility
- Write self-documenting code with descriptive names

### Imports (Python)
- Use absolute imports: `from src.module import function`
- Group imports: stdlib → third-party → local
- Sort alphabetically: `uv run isort .`
- Avoid wildcard imports

### Imports (TypeScript/Vue)
- Group imports: Vue → third-party → local
- Prefer named imports: `import { ref } from 'vue'`
- Use absolute imports with `@/` alias (configured in tsconfig)

### Types
- **Python**: Use type hints for all signatures, prefer `Optional[T]` over `T | None`
- **TypeScript**: Use explicit types over `Any`, prefer `interface` over `type` for objects
- Name type variables: `T`, `K`, `V`, `R` convention

### Naming Conventions
| Type | Convention | Examples |
|------|------------|----------|
| Modules/Python files | snake_case | `knowledge_graph.py` |
| TypeScript files | kebab-case | `knowledge-graph.ts` |
| Vue components | PascalCase | `KnowledgeGraph.vue` |
| Classes | PascalCase | `GraphDatabase` |
| Functions/methods | snake_case | `build_index()` |
| Variables | snake_case | `node_count` |
| Constants | UPPER_SNAKE_CASE | `MAX_DEPTH` |
| Component props (Vue) | camelCase | `isOpen` |
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
- Use `v-if`/`v-show` appropriately (v-show for toggling, v-if for conditional rendering)

### Tailwind CSS
- Use semantic color names: `text-surface-600`, `bg-primary-500`
- Follow spacing scale: `p-4`, `m-2`, `gap-3`
- Use responsive prefixes: `md:flex`, `lg:w-64`
- Group related classes in consistent order: layout → spacing → typography → colors

## Git Workflow

### Commit Principles
- **Atomic commits**: One feature/fix per commit
- **Working state**: Every commit should leave the codebase in a working state
- **Traceable**: From any commit, `git checkout` should produce a runnable codebase

### Files to Commit
```bash
# Always commit
- Source code (*.py, *.vue, *.ts, *.tsx)
- Configuration files (pyproject.toml, package.json, tsconfig.json)
- Package lockfiles (requirements.lock, package-lock.json)
- Test files

# Usually commit
- Documentation (README.md, docs/)
- Scripts and tools
- Git configuration (.gitignore is auto-committed)

# Never commit
- Build output (dist/, __pycache__/, *.pyc)
- Environment files (.env, .env.*)
- IDE configs (.vscode/, .idea/)
- Temporary files (*.tmp, *.swp)
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

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch for next release
- `feature/*`: New features
- `fix/*`: Bug fixes
- `hotfix/*`: Emergency production fixes

## Security
- Never commit secrets, keys, or credentials
- Use environment variables for sensitive configuration
- Validate and sanitize all user inputs
- Use parameterized queries for database operations

## Configuration
- Use environment-specific config files (dev, staging, prod)
- Never hardcode configuration values
- Document all configuration options
