from backend.db.neo4j_client import Neo4jClient
from backend.config import Neo4jConfig
import os

def test():
    config = Neo4jConfig()
    client = Neo4jClient(neo4j_config=config)
    try:
        print("Ensuring project nodes...")
        client.ensure_project_nodes()
        print("Testing get_knowledge_graph_stats...")
        kg_stats = client.get_knowledge_graph_stats()
        print(f"KG Stats: {kg_stats}")
        
        print("Testing get_graph_stats...")
        graph_stats = client.get_graph_stats()
        print(f"Graph Stats: {graph_stats}")
    except Exception as e:
        print(f"FAILED with error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    test()
