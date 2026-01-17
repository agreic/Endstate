![Logo](Logo.png)

# Endstate

Knowledge-graph powered learning with Neo4j database integration.

## Overview

Endstate is a learning platform powered by graph databases, providing intelligent knowledge representation and relationship mapping. The project uses Neo4j for storing and querying complex relationships between concepts, enabling advanced learning analytics and personalized recommendations.

## Features

- 🧠 **Knowledge Graph**: Neo4j-powered graph database for concept relationships
- 🐳 **Container Management**: Automated Docker container lifecycle for Neo4j
- 🔍 **Advanced Querying**: Full Cypher query support with Python client
- 🧪 **Testing Infrastructure**: Comprehensive test suite with shared containers
- 🔒 **Type Safety**: Full type hints and robust error handling
- ⚡ **Performance**: Optimized database operations and connection management

## Architecture

```
endstate/
├── frontend/           # Vue 3 + TypeScript + Tailwind CSS
│   ├── src/           # Source code
│   ├── public/        # Static assets
│   └── dist/          # Build output
├── db/                # Neo4j database integration
│   ├── client.py      # Database client with CRUD operations
│   ├── container.py   # Docker container management
│   ├── exceptions.py  # Custom exception classes
│   └── tests/         # Comprehensive test suite
├── src/               # Python backend services
└── tests/             # Integration tests
```

## Database Module

The `db/` module provides a complete Neo4j integration with:

### Core Components

- **DatabaseClient**: Full CRUD operations for nodes and relationships
- **Neo4jContainer**: Automated Docker container management
- **Comprehensive Testing**: 33 test cases covering all functionality

### Quick Start

```python
from db.client import DatabaseClient
from db.container import Neo4jContainer

# Start Neo4j container
with Neo4jContainer() as container:
    # Connect to database
    with DatabaseClient(container.get_connection_uri(), password="testpassword") as client:
        # Create learning concepts
        python = client.add_node("Language", {"name": "Python", "type": "programming"})
        oop = client.add_node("Concept", {"name": "OOP", "type": "paradigm"})
        
        # Define relationships
        client.add_relationship(
            "Language", {"name": "Python"},
            "IMPLEMENTS",
            "Concept", {"name": "OOP"}
        )
        
        # Query learning paths
        result = client.query("""
            MATCH (lang:Language)-[:IMPLEMENTS]->(concept:Concept)
            RETURN lang.name as language, concept.name as concept
        """)
```

### Installation

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

### Backend & Database

```bash
# Run database tests
uv run pytest tests/db/ -v

# Example usage
uv run python db/example.py

# Integration tests
uv run pytest tests/db/test_integration.py -v
```

## Testing

The project includes comprehensive testing:

```bash
# Run all tests
uv run pytest

# Database module tests
uv run pytest tests/db/ -v

# Frontend tests
cd frontend && npm test
```

**Testing Features:**
- Shared Neo4j container instances for efficiency
- Automatic cleanup between tests
- End-to-end integration testing
- Performance testing with large datasets

## Dependencies

### Core Dependencies
- `neo4j>=5.15.0` - Official Neo4j Python driver
- `docker>=6.1.0` - Docker Python SDK

### Development Dependencies
- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support

### Frontend Dependencies
- Vue 3 + TypeScript
- Tailwind CSS
- Vite build tool

## Usage Examples

### Knowledge Graph Management

```python
# Create learning modules
module = client.add_node("Module", {
    "title": "Python Basics",
    "difficulty": "beginner",
    "duration": 60
})

# Add prerequisites
prereq = client.add_node("Module", {"title": "Programming Fundamentals"})

client.add_relationship(
    "Module", {"title": "Python Basics"},
    "REQUIRES",
    "Module", {"title": "Programming Fundamentals"}
)
```

### Learning Path Discovery

```python
# Find optimal learning paths
paths = client.query("""
    MATCH path = (start:Module)-[:REQUIRES*]->(end:Module)
    WHERE start.title = $start_module
    RETURN [node in nodes(path) | node.title] as learning_path
    ORDER BY length(path) DESC
    LIMIT 5
""", {"start_module": "Advanced Python"})
```

## API Reference

### Database Operations

```python
# Node CRUD
node = client.add_node("Person", {"name": "Alice"})
found = client.search_nodes(label="Person")
updated = client.update_node(node["id"], {"age": 30})
deleted = client.delete_node(node["id"])

# Relationship CRUD
rel = client.add_relationship("Person", {"name": "Alice"}, "KNOWS", "Person", {"name": "Bob"})
relationships = client.get_relationships(node_id=node["id"])
client.delete_relationship(rel["id"])
```

### Container Management

```python
# Custom container configuration
container = Neo4jContainer(
    image="neo4j:5.15",
    password="custom_password",
    name="learning_graph_db"
)

container.start()
uri = container.get_connection_uri()
container.stop()
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Add your license information here]

## Docker Requirements

- Docker Engine running locally
- Neo4j Docker image available
- Sufficient memory (recommended 2GB+ for containers)
