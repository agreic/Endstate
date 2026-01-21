"""
Clear all nodes and relationships from Neo4j.
Run: uv run python scripts/clear_graph.py
"""
from backend.config import Neo4jConfig
from backend.db.neo4j_client import Neo4jClient


def main() -> int:
    config = Neo4jConfig()
    client = Neo4jClient(config)
    client.clean_graph()
    client.close()
    print("Graph cleared successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
