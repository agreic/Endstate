"""Example usage of the database module."""

from db.client import DatabaseClient
from db.container import Neo4jContainer


def main() -> None:
    """Example usage of the database system."""
    # Start a Neo4j container
    with Neo4jContainer(name="neo4j-example") as container:
        print(f"Neo4j running at: {container.get_connection_uri()}")
        print(f"Neo4j browser at: {container.get_http_uri()}")
        
        # Connect to the database
        with DatabaseClient(
            container.get_connection_uri(),
            password="testpassword"
        ) as client:
            
            # Create some sample data
            print("Creating sample data...")
            
            # Create nodes
            alice = client.add_node("Person", {"name": "Alice", "age": 30})
            bob = client.add_node("Person", {"name": "Bob", "age": 25})
            techcorp = client.add_node("Company", {"name": "TechCorp", "industry": "Technology"})
            
            # Create relationships
            client.add_relationship(
                "Person", {"name": "Alice"},
                "WORKS_FOR",
                "Company", {"name": "TechCorp"},
                {"position": "Engineer", "since": 2020}
            )
            
            client.add_relationship(
                "Person", {"name": "Alice"},
                "KNOWS",
                "Person", {"name": "Bob"},
                {"since": 2019}
            )
            
            # Search for nodes
            print("\nSearching for people...")
            people = client.search_nodes(label="Person")
            for person in people:
                print(f"  {person['properties']['name']} (age {person['properties']['age']})")
            
            # Query relationships
            print("\nFinding work relationships...")
            work_rels = client.get_relationships(relationship_type="WORKS_FOR")
            for rel in work_rels:
                print(f"  {rel['type']}: position={rel['properties'].get('position')}")
            
            # Raw Cypher query
            print("\nRunning custom query...")
            result = client.query("""
                MATCH (p:Person)-[r:WORKS_FOR]->(c:Company)
                RETURN p.name as person, c.name as company, r.position as position
            """)
            
            for row in result:
                print(f"  {row['person']} works at {row['company']} as {row['position']}")
            
            print("\nExample completed successfully!")


if __name__ == "__main__":
    main()