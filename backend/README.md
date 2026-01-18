# Endstate Backend

Modular backend for the Endstate knowledge-graph powered learning platform.

## Structure

```
backend/
├── __init__.py           # Main exports
├── config.py             # Configuration management
├── db/                   # Database layer
│   ├── __init__.py
│   └── neo4j_client.py   # Neo4j operations
├── llm/                  # LLM layer
│   ├── __init__.py
│   ├── provider.py       # LLM providers (Ollama, Gemini)
│   └── graph_transformer.py  # Text to graph conversion
├── schemas/              # Graph schemas
│   ├── __init__.py
│   ├── base.py           # Base schema class
│   └── skill_graph.py    # Skill dependency schemas
├── services/             # Service layer
│   ├── __init__.py
│   └── knowledge_graph.py  # High-level KG service
└── examples/             # Usage examples
    └── basic_usage.py
```

## Quick Start

```python
from backend import KnowledgeGraphService

# Initialize (uses Gemini by default)
service = KnowledgeGraphService()

# Or use local Ollama
service = KnowledgeGraphService(llm_provider="ollama")

# Extract and add to graph
await service.aextract_and_add('''
    Python requires understanding variables.
    Functions require understanding variables and control flow.
''')

# Query the graph
service.query("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 10")

# Get statistics
print(service.get_stats())

# Clean the graph
service.clean()

# Merge duplicate nodes
service.merge_duplicates("Skill")
```

## Configuration

### Environment Variables

Create a `.env` file (see `.env.example`):

```bash
# LLM Provider
LLM_PROVIDER=gemini  # or "ollama"

# Gemini API
GOOGLE_API_KEY=your_api_key

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
```

### Custom Schemas

```python
from backend.schemas.base import GraphSchema

# Define custom schema
MySchema = GraphSchema(
    name="My Custom Schema",
    description="Custom schema for my use case",
    allowed_nodes=["Entity1", "Entity2"],
    allowed_relationships=[
        ("Entity1", "RELATES_TO", "Entity2"),
    ],
    node_properties=["name", "description"],
    relationship_properties=["weight"],
    strict_mode=True,
)

# Use with service
service = KnowledgeGraphService(schema=MySchema)
```

## API Reference

### KnowledgeGraphService

Main service class combining LLM and database operations.

**Extraction:**
- `extract(text)` - Extract graph from text (sync)
- `aextract(text)` - Extract graph from text (async)
- `extract_and_add(text)` - Extract and add to DB (sync)
- `aextract_and_add(text)` - Extract and add to DB (async)

**Graph Management:**
- `clean()` - Delete all nodes and relationships
- `clean_by_label(label)` - Delete nodes with specific label
- `merge_duplicates(label)` - Merge duplicate nodes
- `merge_all_duplicates()` - Merge all duplicates

**Queries:**
- `query(cypher, params)` - Execute Cypher query
- `get_stats()` - Get graph statistics
- `get_nodes(label, limit)` - Get nodes
- `get_relationships(limit)` - Get relationships
- `visualize()` - Get visualization data

### Neo4jClient

Low-level database operations.

### GraphTransformer

LLM-based text to graph transformation.

## Predefined Schemas

- `SkillGraphSchema` - Full schema for learning paths (default)
- `MinimalSkillSchema` - Simplified skill dependencies
- `ContentExtractionSchema` - Extract from educational content

## Running Examples

```bash
# With Gemini
python -m backend.examples.basic_usage

# With Ollama
LLM_PROVIDER=ollama python -m backend.examples.basic_usage
```

## Dependencies

- `langchain-neo4j` - LangChain Neo4j integration
- `langchain-experimental` - Graph transformers
- `langchain-ollama` - Ollama LLM support
- `langchain-google-genai` - Gemini LLM support
- `neo4j` - Neo4j Python driver
- `neo4j-viz` - Graph visualization (optional)
