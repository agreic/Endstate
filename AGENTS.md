# AGENTS.md - Endstate Development Guide

This file provides guidelines for agentic coding agents working on the Endstate project.

## Build, Lint, and Test Commands

### Dependency Management
- **Install dependencies**: `uv sync`
- **Add a dependency**: `uv add <package>` or `uv add --dev <package>`
- **Remove a dependency**: `uv remove <package>`
- **Update dependencies**: `uv sync --upgrade`

### Testing
- **Run all tests**: `uv run pytest`
- **Run a single test file**: `uv run pytest tests/test_file.py`
- **Run a single test**: `uv run pytest tests/test_file.py::test_function_name`
- **Run tests with coverage**: `uv run pytest --cov=src --cov-report=term-missing`
- **Run tests in verbose mode**: `uv run pytest -v`
- **Run tests matching a pattern**: `uv run pytest -k "test_name_pattern"`

## Code Style Guidelines

### General Principles
- Write clean, readable, and maintainable code
- Favor simplicity over cleverness
- Keep functions and modules focused on a single responsibility
- Write self-documenting code with descriptive names

### Imports
- Use absolute imports: `from src.module import function` (not `from .module import function`)
- Group imports in this order: standard library, third-party, local application
- Sort imports alphabetically within each group: `uv run isort .`
- Avoid wildcard imports (`from module import *`)
- Use explicit re-exports: `from module import ClassName` for public APIs

### Types
- Use type hints for all function signatures and method definitions
- Prefer explicit types over `Any`: use `Unknown`, `TypeVar`, or `Protocol` when appropriate
- Use `Optional[T]` instead of `T | None` for compatibility (or vice versa consistently)
- Name type variables with `T`, `K`, `V`, `R` convention: `T = TypeVar("T")`
- Use `TypedDict` for structured dictionaries with specific keys
- Import types from `typing` module, not from the class itself

### Naming Conventions
- **Modules**: lowercase with underscores: `knowledge_graph.py`
- **Classes**: PascalCase: `GraphDatabase`, `LearningEngine`
- **Functions/methods**: snake_case: `build_index()`, `train_model()`
- **Variables**: snake_case: `node_count`, `embedding_vector`
- **Constants**: UPPER_SNAKE_CASE: `MAX_DEPTH`, `DEFAULT_TIMEOUT`
- **Type aliases**: PascalCase: `GraphNode = dict[str, Any]`
- **Private attributes/methods**: leading underscore: `_cache`, `_build_cache()`

### Error Handling
- Use explicit exception types, never catch bare `except:`
- Create custom exception classes for domain-specific errors
- Prefer early returns with error conditions over nested if-else
- Use context managers (`with`) for resource management
- Log errors with appropriate level before re-raising if needed
- Wrap external API calls with specific exception handling

### Async Code
- Use `async def` for I/O-bound operations
- Never block in async code; use `await` or run in executor
- Use `asyncio.gather()` for concurrent operations
- Add reasonable timeouts to async operations: `await asyncio.wait_for(coro, timeout=30)`

### Graph and Learning Code Specifics
- Document graph traversal algorithms and their complexity
- Use typed edges and nodes: `Edge[Source, Target]`
- Validate graph connectivity and acyclicity where applicable
- Log embedding dimensions, model sizes, and training metrics
- Cache embeddings and computed features with expiration policies
- Use batch processing for large graph operations

### Testing
- Write tests for all public functions and classes
- Use fixtures for common setup: `pytest.fixture`
- Mock external services and I/O operations
- Aim for meaningful test names: `test_cypher_query_parses_complex_pattern()`
- Keep tests fast; mark slow tests with `@pytest.mark.slow`
- Use `pytest.mark.parametrize` for similar test cases

### Documentation
- Use docstrings for all public modules, classes, and functions
- Docstring style: Google format or NumPy format (be consistent)
- Document exceptions that functions may raise
- Include type hints in docstrings for complex types
- Add examples in docstrings for complex public APIs

### Git and Workflow
- Make atomic commits: one feature/fix per commit
- Write meaningful commit messages: "Add vector search index for graph nodes"
- Run linting and tests before committing

### Security
- Never commit secrets, keys, or credentials
- Use environment variables for sensitive configuration
- Validate and sanitize all user inputs
- Use parameterized queries for database operations
- Keep dependencies updated: `uv pip install --upgrade <package>`

### Configuration Management
- Use environment-specific config files (dev, staging, prod)
- Never hardcode configuration values
- Implement config validation at startup
- Document all configuration options
