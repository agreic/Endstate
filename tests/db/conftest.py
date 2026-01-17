"""Test configuration and fixtures for database tests."""

import pytest
from typing import Generator

from db.container import Neo4jContainer
from db.client import DatabaseClient


@pytest.fixture(scope="session")
def neo4j_container() -> Generator[Neo4jContainer, None, None]:
    """Shared Neo4j container for all database tests."""
    container = Neo4jContainer()
    
    try:
        container.start()
        yield container
    finally:
        container.stop()
        # Clean up any orphaned volumes
        _cleanup_orphaned_volumes()


def _cleanup_orphaned_volumes() -> None:
    """Clean up any orphaned Neo4j volumes."""
    try:
        import docker
        client = docker.from_env()
        
        # Get all volumes with neo4j in name or test
        volumes = client.volumes.list()
        for volume in volumes:
            volume_name = volume.name
            if (volume_name and 
                ("neo4j" in volume_name.lower() or 
                 "test" in volume_name.lower())):
                try:
                    volume.remove(force=True)
                except Exception:
                    pass
    except Exception:
        pass


@pytest.fixture
def db_client(neo4j_container: Neo4jContainer) -> Generator[DatabaseClient, None, None]:
    """Database client connected to the shared container."""
    uri = neo4j_container.get_connection_uri()
    client = DatabaseClient(uri, password="testpassword")
    
    try:
        client.connect()
        yield client
    finally:
        # Clean up database after each test
        client.query("MATCH (n) DETACH DELETE n")
        client.disconnect()


@pytest.fixture
def sample_data(db_client: DatabaseClient) -> None:
    """Create sample data for testing."""
    # Create sample nodes
    db_client.add_node("Person", {"name": "Alice", "age": 30})
    db_client.add_node("Person", {"name": "Bob", "age": 25})
    db_client.add_node("Company", {"name": "TechCorp", "industry": "Technology"})
    db_client.add_node("Company", {"name": "FinanceCo", "industry": "Finance"})
    
    # Create sample relationships
    db_client.add_relationship(
        "Person", {"name": "Alice"},
        "WORKS_FOR",
        "Company", {"name": "TechCorp"},
        {"position": "Engineer", "since": 2020}
    )
    db_client.add_relationship(
        "Person", {"name": "Bob"},
        "WORKS_FOR",
        "Company", {"name": "FinanceCo"},
        {"position": "Analyst", "since": 2021}
    )
    db_client.add_relationship(
        "Person", {"name": "Alice"},
        "KNOWS",
        "Person", {"name": "Bob"},
        {"since": 2019}
    )