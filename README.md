![Logo](Logo.png)

# Endstate

Knowledge-graph powered learning platform.

## Overview

Endstate is a learning platform for intelligent knowledge representation and relationship mapping.

## Architecture

```
endstate/
├── frontend/           # Vue 3 + TypeScript + Tailwind CSS
│   ├── src/           # Source code
│   ├── public/        # Static assets
│   └── dist/          # Build output
├── src/               # Python backend services
└── tests/             # Test files
```

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
