"""
Seed script to populate Neo4j with sample skill graph data.
Run: cd backend && uv run python ../scripts/seed_graph.py
"""
from db.neo4j_client import Neo4jClient
from config import Neo4jConfig


def seed_sample_data():
    """Add sample skill graph data to Neo4j."""
    
    config = Neo4jConfig(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password123",
        database="neo4j",
    )
    
    with Neo4jClient(neo4j_config=config) as client:
        # Clean existing data
        print("Cleaning existing data...")
        client.clean_graph()
        
        print("Adding skills...")
        
        # Create Skills
        skills = [
            ("python", "Python", "Programming language"),
            ("variables", "Variables", "Container for storing data"),
            ("data_types", "Data Types", "Types of data in Python"),
            ("functions", "Functions", "Reusable blocks of code"),
            ("oop", "Object-Oriented Programming", "Programming paradigm"),
            ("django", "Django", "Python web framework"),
            ("flask", "Flask", "Lightweight Python web framework"),
            ("databases", "Databases", "Structured data storage"),
            ("sql", "SQL", "Query language for databases"),
            ("git", "Git", "Version control system"),
            ("docker", "Docker", "Containerization platform"),
            ("api", "APIs", "Application Programming Interfaces"),
            ("rest", "REST", "Architectural style for APIs"),
            ("javascript", "JavaScript", "Programming language for web"),
            ("html_css", "HTML/CSS", "Web page structure and styling"),
        ]
        
        for skill_id, name, description in skills:
            client.query("""
                CREATE (s:Skill {
                    id: $id,
                    name: $name,
                    description: $description,
                    difficulty: 'beginner',
                    importance: 'core'
                })
            """, {"id": skill_id, "name": name, "description": description})
        
        print("Adding concepts...")
        
        concepts = [
            ("programming_basics", "Programming Basics", "Fundamental programming concepts"),
            ("web_development", "Web Development", "Building websites and web apps"),
            ("backend_dev", "Backend Development", "Server-side development"),
            ("devops", "DevOps", "Development and operations practices"),
        ]
        
        for concept_id, name, description in concepts:
            client.query("""
                CREATE (c:Concept {
                    id: $id,
                    name: $name,
                    description: $description
                })
            """, {"id": concept_id, "name": name, "description": description})
        
        print("Adding relationships...")
        
        # Skill dependencies
        relationships = [
            # Python fundamentals
            ("variables", "REQUIRES", "python"),
            ("data_types", "REQUIRES", "python"),
            ("data_types", "REQUIRES", "variables"),
            ("functions", "REQUIRES", "python"),
            ("oop", "REQUIRES", "python"),
            ("oop", "REQUIRES", "functions"),
            
            # Web development
            ("django", "REQUIRES", "python"),
            ("django", "REQUIRES", "databases"),
            ("flask", "REQUIRES", "python"),
            ("flask", "REQUIRES", "databases"),
            ("api", "REQUIRES", "python"),
            ("rest", "REQUIRES", "api"),
            
            # Database
            ("sql", "REQUIRES", "databases"),
            
            # DevOps
            ("docker", "REQUIRES", "git"),
            
            # Web basics
            ("javascript", "RELATED_TO", "python"),
            ("html_css", "RELATED_TO", "javascript"),
            
            # Concepts
            ("python", "PART_OF", "programming_basics"),
            ("variables", "PART_OF", "programming_basics"),
            ("data_types", "PART_OF", "programming_basics"),
            ("functions", "PART_OF", "programming_basics"),
            
            ("django", "PART_OF", "web_development"),
            ("flask", "PART_OF", "web_development"),
            ("html_css", "PART_OF", "web_development"),
            ("javascript", "PART_OF", "web_development"),
            
            ("django", "PART_OF", "backend_dev"),
            ("flask", "PART_OF", "backend_dev"),
            ("databases", "PART_OF", "backend_dev"),
            ("api", "PART_OF", "backend_dev"),
            ("docker", "PART_OF", "devops"),
        ]
        
        for source_id, rel_type, target_id in relationships:
            client.query(f"""
                MATCH (s:Skill {{id: $source_id}})
                MATCH (t:Skill {{id: $target_id}})
                CREATE (s)-[:{rel_type} {{strength: 0.8}}]->(t)
            """, {"source_id": source_id, "target_id": target_id})
        
        # Concept relationships
        concept_rels = [
            ("programming_basics", "CONTAINS", "python"),
            ("programming_basics", "CONTAINS", "variables"),
            ("web_development", "CONTAINS", "django"),
            ("web_development", "CONTAINS", "html_css"),
            ("backend_dev", "CONTAINS", "django"),
            ("backend_dev", "CONTAINS", "databases"),
        ]
        
        for source_id, rel_type, target_id in concept_rels:
            client.query(f"""
                MATCH (s:Concept {{id: $source_id}})
                MATCH (t:Skill {{id: $target_id}})
                CREATE (s)-[:{rel_type}]->(t)
            """, {"source_id": source_id, "target_id": target_id})
        
        # Get stats
        stats = client.get_graph_stats()
        print(f"\nGraph created successfully!")
        print(f"  Total nodes: {stats['total_nodes']}")
        print(f"  Total relationships: {stats['total_relationships']}")
        print(f"  Nodes by type: {stats['nodes']}")
        print(f"  Relationships by type: {stats['relationships']}")


if __name__ == "__main__":
    seed_sample_data()
