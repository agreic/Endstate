"""Integration tests for the complete database system."""

import pytest
from db.client import DatabaseClient
from db.container import Neo4jContainer


class TestIntegration:
    """Integration tests for container and client working together."""
    
    def test_full_workflow(self) -> None:
        """Test complete workflow from container start to database operations."""
        with Neo4jContainer(name="neo4j-integration-test") as container:
            # Connect to database
            with DatabaseClient(
                container.get_connection_uri(),
                password="testpassword"
            ) as client:
                
                # Create nodes
                person = client.add_node("Person", {"name": "John", "age": 40})
                company = client.add_node("Company", {"name": "TechInc"})
                
                # Create relationship
                rel = client.add_relationship(
                    "Person", {"name": "John"},
                    "WORKS_FOR",
                    "Company", {"name": "TechInc"},
                    {"position": "CTO"}
                )
                
                # Query data
                results = client.query("""
                    MATCH (p:Person)-[r:WORKS_FOR]->(c:Company)
                    RETURN p.name as person, c.name as company, r.position as position
                """)
                
                assert len(results) == 1
                assert results[0]["person"] == "John"
                assert results[0]["company"] == "TechInc"
                assert results[0]["position"] == "CTO"
                
                # Update node
                updated = client.update_node(person["id"], {"age": 41})
                assert updated["properties"]["age"] == 41
                
                # Delete relationship
                success = client.delete_relationship(rel["id"])
                assert success is True
                
                # Delete nodes
                success = client.delete_node(person["id"])
                assert success is True
                
                success = client.delete_node(company["id"])
                assert success is True
                
                # Verify everything is deleted
                remaining = client.query("MATCH (n) RETURN count(n) as count")
                assert remaining[0]["count"] == 0
    
    def test_concurrent_clients(self, neo4j_container) -> None:
        """Test multiple clients connecting to the same container."""
        uri = neo4j_container.get_connection_uri()
        
        # Create multiple clients
        clients = []
        for i in range(3):
            client = DatabaseClient(uri, password="testpassword")
            client.connect()
            clients.append(client)
        
        try:
            # Each client creates a node
            for i, client in enumerate(clients):
                client.add_node("TestNode", {"client_id": i, "value": i * 10})
            
            # Verify all nodes exist
            all_nodes = clients[0].search_nodes(label="TestNode")
            assert len(all_nodes) == 3
            
            # Clean up
            for node in all_nodes:
                clients[0].delete_node(node["id"])
                
        finally:
            # Disconnect all clients
            for client in clients:
                client.disconnect()
    
    def test_error_handling(self, neo4j_container) -> None:
        """Test error handling throughout the system."""
        uri = neo4j_container.get_connection_uri()
        client = DatabaseClient(uri, password="testpassword")
        
        # Test operations without connection
        with pytest.raises(Exception):  # Should raise ConnectionError
            client.add_node("Test", {})
        
        # Connect and test query errors
        client.connect()
        
        with pytest.raises(Exception):  # Should raise QueryError
            client.query("INVALID QUERY")
        
        client.disconnect()
    
    def test_large_dataset(self, db_client: DatabaseClient) -> None:
        """Test handling of larger datasets."""
        # Create many nodes
        node_ids = []
        for i in range(100):
            node = db_client.add_node("DataNode", {"index": i, "value": f"data_{i}"})
            node_ids.append(node["id"])
        
        # Create relationships between consecutive nodes
        for i in range(99):
            db_client.add_relationship(
                "DataNode", {"index": i},
                "NEXT",
                "DataNode", {"index": i + 1}
            )
        
        # Query with pagination
        first_10 = db_client.search_nodes(label="DataNode", limit=10)
        assert len(first_10) == 10
        
        # Count all nodes
        count_result = db_client.query("MATCH (n:DataNode) RETURN count(n) as count")
        assert count_result[0]["count"] == 100
        
        # Count all relationships
        rel_count = db_client.query("MATCH ()-[r:NEXT]->() RETURN count(r) as count")
        assert rel_count[0]["count"] == 99
        
        # Clean up
        for node_id in node_ids:
            db_client.delete_node(node_id, detach=True)
        
        # Verify cleanup
        remaining = db_client.query("MATCH (n:DataNode) RETURN count(n) as count")
        assert remaining[0]["count"] == 0