from backend.db.neo4j_client import Neo4jClient
from backend.config import Neo4jConfig
import os

def test():
    config = Neo4jConfig()
    client = Neo4jClient(neo4j_config=config)
    try:
        print("Testing ensure_project_nodes...")
        client.ensure_project_nodes()
        print("Testing get_knowledge_graph_stats...")
        stats = client.get_knowledge_graph_stats()
        print(f"Stats: {stats}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    test()
