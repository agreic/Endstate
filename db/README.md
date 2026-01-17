# Database Module

A comprehensive Neo4j database integration module with Docker container management for testing and development. This module provides a clean, type-safe interface for working with graph data while handling all the complexity of container lifecycle management.

## Features

- 🐳 **Container Management**: Automated Neo4j Docker container lifecycle with health checks
- 🔗 **Database Client**: Full CRUD operations for nodes and relationships
- 🧪 **Testing Support**: Shared container instances with automatic cleanup
- 🔒 **Type Safety**: Full type hints and comprehensive error handling
- ⚡ **Performance**: Connection pooling and optimized queries
- 📊 **Querying**: Raw Cypher query support with parameter binding

## Quick Start

```python
from db.client import DatabaseClient
from db.container import Neo4jContainer

# Start Neo4j container
with Neo4jContainer() as container:
    # Connect to database
    with DatabaseClient(container.get_connection_uri(), password="testpassword") as client:
        # Add a node
        node = client.add_node("Person", {"name": "Alice", "age": 30})
        
        # Search nodes
        people = client.search_nodes(label="Person")
        
        # Raw Cypher query
        result = client.query("MATCH (n:Person) RETURN n.name as name")
```

## API Reference

### Neo4jContainer

Manages Neo4j Docker containers for testing and development.

```python
from db.container import Neo4jContainer

# Basic usage
with Neo4jContainer() as container:
    uri = container.get_connection_uri()  # bolt://localhost:7687
    http_uri = container.get_http_uri()   # http://localhost:7474

# Advanced configuration
container = Neo4jContainer(
    image="neo4j:5.15",
    password="custompassword",
    port=7687,
    http_port=7474,
    name="my-neo4j"
)

container.start()
uri = container.get_connection_uri()
container.stop()
```

**Methods:**
- `start()` - Start the container and wait for readiness
- `stop()` - Stop and remove the container
- `get_connection_uri()` - Get Bolt connection URI
- `get_http_uri()` - Get HTTP interface URI
- `is_running()` - Check container status

### DatabaseClient

Neo4j database client with full CRUD operations and query capabilities.

```python
from db.client import DatabaseClient

# Context manager usage (recommended)
with DatabaseClient(uri, username="neo4j", password="password") as client:
    # All operations here
    pass

# Manual connection management
client = DatabaseClient(uri, username="neo4j", password="password")
client.connect()
try:
    # Operations here
    pass
finally:
    client.disconnect()
```

**Node Operations:**
```python
# Create nodes
node = client.add_node("Person", {"name": "Alice", "age": 30})
node_without_props = client.add_node("Company")

# Search nodes
all_people = client.search_nodes(label="Person")
alice = client.search_nodes(properties={"name": "Alice"})
limited = client.search_nodes(limit=10)

# Get specific node
found = client.get_node_by_id(node["id"])

# Update nodes
updated = client.update_node(
    node["id"], 
    properties={"age": 31},
    add_labels=["Employee"],
    remove_labels=["Person"]
)

# Delete nodes
deleted = client.delete_node(node["id"], detach=True)  # Remove relationships too
```

**Relationship Operations:**
```python
# Create relationships
rel = client.add_relationship(
    from_label="Person", from_properties={"name": "Alice"},
    relationship_type="KNOWS",
    to_label="Person", to_properties={"name": "Bob"},
    relationship_properties={"since": 2020}
)

# Get relationships
all_rels = client.get_relationships()
work_rels = client.get_relationships(relationship_type="WORKS_FOR")
outgoing = client.get_relationships(node_id=node["id"], direction="out")

# Delete relationships
deleted = client.delete_relationship(rel["id"])
```

**Query Operations:**
```python
# Raw Cypher queries
result = client.query("MATCH (n:Person) RETURN n.name as name")
count = client.query("MATCH (n) RETURN count(n) as count")

# Parameterized queries
params = {"name": "Alice"}
result = client.query("MATCH (p:Person {name: $name}) RETURN p", params)

# Process results
for record in result:
    print(record["name"])  # Access by column name
```

## Testing

The module includes comprehensive tests with shared container instances to ensure efficiency and reliability:

```bash
# Run all database tests
uv run pytest tests/db/ -v

# Run specific test categories
uv run pytest tests/db/test_client.py -v          # Client operations
uv run pytest tests/db/test_container.py -v       # Container management
uv run pytest tests/db/test_integration.py -v     # End-to-end workflows

# Run specific test
uv run pytest tests/db/test_client.py::TestDatabaseClient::test_add_node -v
```

**Test Features:**
- Session-scoped shared container (runs once per test session)
- Automatic database cleanup between tests
- Comprehensive coverage of all API methods
- Integration tests for complete workflows
- Error handling validation
- Performance testing with large datasets

## Dependencies

```toml
[dependencies]
neo4j = ">=5.15.0"    # Official Neo4j Python driver
docker = ">=6.1.0"     # Docker Python SDK

[dev-dependencies]
pytest = ">=7.4.0"     # Testing framework
pytest-asyncio = ">=0.21.0"  # Async testing support
```

## Error Handling

The module provides a robust exception hierarchy for different failure scenarios:

```python
from db.exceptions import ContainerError, ConnectionError, QueryError, DatabaseError

try:
    with Neo4jContainer() as container:
        with DatabaseClient(container.get_connection_uri()) as client:
            # Database operations
            pass
except ContainerError as e:
    print(f"Container issue: {e}")
except ConnectionError as e:
    print(f"Connection issue: {e}")
except QueryError as e:
    print(f"Query issue: {e}")
except DatabaseError as e:
    print(f"Database issue: {e}")
```

**Exception Types:**
- `ContainerError` - Docker container lifecycle issues
- `ConnectionError` - Database connection/authentication problems  
- `QueryError` - Cypher query syntax or execution failures
- `DatabaseError` - Base database exception class

## Examples

### Basic Graph Operations

```python
from db.client import DatabaseClient
from db.container import Neo4jContainer

with Neo4jContainer() as container:
    with DatabaseClient(container.get_connection_uri(), password="testpassword") as client:
        # Create a social network
        alice = client.add_node("Person", {"name": "Alice", "age": 30})
        bob = client.add_node("Person", {"name": "Bob", "age": 25})
        techcorp = client.add_node("Company", {"name": "TechCorp"})
        
        # Add relationships
        client.add_relationship("Person", {"name": "Alice"}, "WORKS_FOR", "Company", {"name": "TechCorp"})
        client.add_relationship("Person", {"name": "Alice"}, "KNOWS", "Person", {"name": "Bob"})
        
        # Query the network
        friends = client.query("""
            MATCH (alice:Person {name: 'Alice'})-[:KNOWS]->(friends:Person)
            RETURN friends.name as friend_name
        """)
```

### Advanced Search

```python
# Find employees at tech companies
tech_employees = client.search_nodes(
    properties={"industry": "Technology"}
)

# Find people who work together
colleagues = client.get_relationships(
    relationship_type="WORKS_FOR"
)
```

## Performance Considerations

- **Connection Reuse**: Use context managers for optimal connection handling
- **Batch Operations**: For large datasets, consider using raw Cypher queries
- **Indexing**: Add indexes frequently queried properties in Neo4j
- **Transaction Management**: Each operation runs in its own transaction

## Docker Requirements

- Docker Engine running locally
- Neo4j Docker image available (`neo4j:5.15` by default)
- Sufficient memory (recommended 2GB+ for container)

## Volume Management

The module automatically manages Docker volumes to prevent "zombie volumes":

### Automatic Cleanup
- Each container instance uses named volumes (`{name}_data`, `{name}_logs`)
- Volumes are automatically cleaned up when containers are stopped
- Test fixtures clean up orphaned volumes after test completion

### Manual Cleanup
Use the provided cleanup utility:

```bash
# List all Neo4j containers and volumes
PYTHONPATH=. python scripts/cleanup_docker.py list

# Clean up all Neo4j resources
PYTHONPATH=. python scripts/cleanup_docker.py cleanup

# Force cleanup (use with caution)
PYTHONPATH=. python scripts/cleanup_docker.py cleanup --force
```

### Volume Names
- Shared test container: `neo4j-test_data`, `neo4j-test_logs`
- Example containers: `neo4j-example_data`, `neo4j-example_logs`
- Custom containers: `{container_name}_data`, `{container_name}_logs`