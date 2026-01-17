"""Tests for database client operations."""

import pytest
from db.client import DatabaseClient
from db.exceptions import ConnectionError, QueryError


class TestDatabaseClient:
    """Test cases for DatabaseClient class."""
    
    def test_connect_disconnect(self, neo4j_container) -> None:
        """Test connecting to and disconnecting from database."""
        uri = neo4j_container.get_connection_uri()
        client = DatabaseClient(uri, password="testpassword")
        
        # Test connection
        client.connect()
        assert client.driver is not None
        
        # Test disconnection
        client.disconnect()
        assert client.driver is None
    
    def test_context_manager(self, neo4j_container) -> None:
        """Test client as context manager."""
        uri = neo4j_container.get_connection_uri()
        
        with DatabaseClient(uri, password="testpassword") as client:
            assert client.driver is not None
            # Test basic query
            result = client.query("RETURN 1 as test")
            assert len(result) == 1
            assert result[0]["test"] == 1
        
        assert client.driver is None
    
    def test_query_without_connection(self) -> None:
        """Test error when querying without connection."""
        client = DatabaseClient("bolt://localhost:7687")
        
        with pytest.raises(ConnectionError, match="Database not connected"):
            client.query("RETURN 1")
    
    def test_add_node(self, db_client: DatabaseClient) -> None:
        """Test adding a node."""
        result = db_client.add_node("Person", {"name": "Alice", "age": 30})
        
        assert "id" in result
        assert result["labels"] == ["Person"]
        assert result["properties"]["name"] == "Alice"
        assert result["properties"]["age"] == 30
    
    def test_add_node_without_properties(self, db_client: DatabaseClient) -> None:
        """Test adding a node without properties."""
        result = db_client.add_node("Company")
        
        assert "id" in result
        assert result["labels"] == ["Company"]
        assert result["properties"] == {}
    
    def test_add_node_merge(self, db_client: DatabaseClient) -> None:
        """Test adding a node with merge (upsert)."""
        # Add first node
        result1 = db_client.add_node("Person", {"name": "Bob"}, merge=False)
        
        # Add same node with merge (should return existing node)
        result2 = db_client.add_node("Person", {"name": "Bob"}, merge=True)
        
        # MERGE should return the existing node
        assert result1["id"] == result2["id"]
        assert result1["properties"]["name"] == result2["properties"]["name"]
    
    def test_search_nodes_by_label(self, db_client: DatabaseClient, sample_data) -> None:
        """Test searching nodes by label."""
        results = db_client.search_nodes(label="Person")
        
        assert len(results) == 2
        for result in results:
            assert "Person" in result["labels"]
            assert "name" in result["properties"]
    
    def test_search_nodes_by_properties(self, db_client: DatabaseClient, sample_data) -> None:
        """Test searching nodes by properties."""
        results = db_client.search_nodes(properties={"name": "Alice"})
        
        assert len(results) == 1
        assert results[0]["properties"]["name"] == "Alice"
        assert results[0]["properties"]["age"] == 30
    
    def test_search_nodes_with_limit(self, db_client: DatabaseClient, sample_data) -> None:
        """Test searching nodes with limit."""
        results = db_client.search_nodes(limit=2)
        
        assert len(results) <= 2
    
    def test_get_node_by_id(self, db_client: DatabaseClient) -> None:
        """Test getting a node by ID."""
        # Create a node
        created = db_client.add_node("Person", {"name": "Charlie"})
        node_id = created["id"]
        
        # Get the node
        result = db_client.get_node_by_id(node_id)
        
        assert result is not None
        assert result["id"] == node_id
        assert result["properties"]["name"] == "Charlie"
    
    def test_get_node_by_id_not_found(self, db_client: DatabaseClient) -> None:
        """Test getting a non-existent node by ID."""
        result = db_client.get_node_by_id("non-existent-id")
        assert result is None
    
    def test_update_node_properties(self, db_client: DatabaseClient) -> None:
        """Test updating node properties."""
        # Create a node
        created = db_client.add_node("Person", {"name": "Dave", "age": 35})
        node_id = created["id"]
        
        # Update properties
        result = db_client.update_node(node_id, {"age": 36, "city": "New York"})
        
        assert result["id"] == node_id
        assert result["properties"]["name"] == "Dave"  # Unchanged
        assert result["properties"]["age"] == 36  # Updated
        assert result["properties"]["city"] == "New York"  # Added
    
    def test_update_node_labels(self, db_client: DatabaseClient) -> None:
        """Test updating node labels."""
        # Create a node
        created = db_client.add_node("Person", {"name": "Eve"})
        node_id = created["id"]
        
        # Add labels first
        result = db_client.update_node(
            node_id,
            properties={},
            add_labels=["Employee"],
            remove_labels=[]
        )
        
        assert result["id"] == node_id
        assert "Employee" in result["labels"]
        assert "Person" in result["labels"]  # Original label should remain
        
        # Remove labels separately
        result = db_client.update_node(
            node_id,
            properties={},
            add_labels=[],
            remove_labels=["Person"]
        )
        
        assert "Employee" in result["labels"]
        assert "Person" not in result["labels"]
    
    def test_delete_node(self, db_client: DatabaseClient) -> None:
        """Test deleting a node."""
        # Create a node
        created = db_client.add_node("Person", {"name": "Frank"})
        node_id = created["id"]
        
        # Verify node exists
        assert db_client.get_node_by_id(node_id) is not None
        
        # Delete node
        success = db_client.delete_node(node_id)
        assert success is True
        
        # Verify node is gone
        assert db_client.get_node_by_id(node_id) is None
    
    def test_delete_node_not_found(self, db_client: DatabaseClient) -> None:
        """Test deleting a non-existent node."""
        success = db_client.delete_node("non-existent-id")
        assert success is False
    
    def test_add_relationship(self, db_client: DatabaseClient) -> None:
        """Test adding a relationship."""
        # Create nodes
        person = db_client.add_node("Person", {"name": "Grace"})
        company = db_client.add_node("Company", {"name": "Startup"})
        
        # Add relationship
        result = db_client.add_relationship(
            "Person", {"name": "Grace"},
            "WORKS_FOR",
            "Company", {"name": "Startup"},
            {"position": "CEO", "since": 2022}
        )
        
        assert "id" in result
        assert result["type"] == "WORKS_FOR"
        assert result["properties"]["position"] == "CEO"
        assert result["properties"]["since"] == 2022
    
    def test_get_relationships(self, db_client: DatabaseClient, sample_data) -> None:
        """Test getting relationships."""
        # Get all relationships
        results = db_client.get_relationships()
        
        assert len(results) >= 3  # At least the sample relationships
        
        # Get relationships for a specific node
        alice = db_client.search_nodes(properties={"name": "Alice"})[0]
        alice_relationships = db_client.get_relationships(node_id=alice["id"])
        
        assert len(alice_relationships) >= 2  # WORKS_FOR and KNOWS
    
    def test_get_relationships_by_type(self, db_client: DatabaseClient, sample_data) -> None:
        """Test getting relationships by type."""
        results = db_client.get_relationships(relationship_type="WORKS_FOR")
        
        assert len(results) >= 2  # Alice and Bob both work for companies
        for rel in results:
            assert rel["type"] == "WORKS_FOR"
    
    def test_get_relationships_by_direction(self, db_client: DatabaseClient, sample_data) -> None:
        """Test getting relationships by direction."""
        alice = db_client.search_nodes(properties={"name": "Alice"})[0]
        bob = db_client.search_nodes(properties={"name": "Bob"})[0]
        
        # Outgoing relationships from Alice
        outgoing = db_client.get_relationships(node_id=alice["id"], direction="out")
        assert len(outgoing) >= 2  # WORKS_FOR + KNOWS
        
        # Incoming relationships to Bob (from Alice)
        incoming = db_client.get_relationships(node_id=bob["id"], direction="in")
        assert len(incoming) >= 1  # Alice knows Bob (incoming to Bob)
        
        # Both directions
        both = db_client.get_relationships(node_id=alice["id"], direction="both")
        assert len(both) >= len(outgoing)  # Should include all relationships
    
    def test_delete_relationship(self, db_client: DatabaseClient) -> None:
        """Test deleting a relationship."""
        # Create nodes and relationship
        person = db_client.add_node("Person", {"name": "Henry"})
        company = db_client.add_node("Company", {"name": "Corp"})
        
        rel = db_client.add_relationship(
            "Person", {"name": "Henry"},
            "WORKS_FOR",
            "Company", {"name": "Corp"}
        )
        
        rel_id = rel["id"]
        
        # Delete relationship
        success = db_client.delete_relationship(rel_id)
        assert success is True
        
        # Verify relationship is gone
        remaining_rels = db_client.get_relationships()
        for remaining_rel in remaining_rels:
            assert remaining_rel["id"] != rel_id
    
    def test_delete_relationship_not_found(self, db_client: DatabaseClient) -> None:
        """Test deleting a non-existent relationship."""
        success = db_client.delete_relationship("non-existent-id")
        assert success is False
    
    def test_raw_query(self, db_client: DatabaseClient, sample_data) -> None:
        """Test raw Cypher queries."""
        # Count nodes
        result = db_client.query("MATCH (n) RETURN count(n) as count")
        assert result[0]["count"] == 4  # 2 Person + 2 Company
        
        # Complex query
        result = db_client.query("""
            MATCH (p:Person)-[r:WORKS_FOR]->(c:Company)
            RETURN p.name as person, c.name as company, r.position as position
        """)
        
        assert len(result) == 2
        for row in result:
            assert row["person"] is not None  # Access record data by key
            assert row["company"] is not None
            assert row["position"] is not None
    
    def test_query_error(self, db_client: DatabaseClient) -> None:
        """Test handling of query errors."""
        with pytest.raises(QueryError):
            db_client.query("INVALID CYPHER SYNTAX")