#!/bin/bash
# Seed Neo4j with sample skill graph data
# Usage: ./scripts/seed.sh

cd "$(dirname "$0")/.."

echo "Seeding Neo4j with sample data..."
PYTHONPATH=./backend uv run python -c "
from backend.db.neo4j_client import Neo4jClient
from backend.config import Neo4jConfig

config = Neo4jConfig()
client = Neo4jClient(config)
client.clean_graph()

skills = [
    ('python', 'Python', 'Programming language'),
    ('variables', 'Variables', 'Container for storing data'),
    ('data_types', 'Data Types', 'Types of data in Python'),
    ('functions', 'Functions', 'Reusable blocks of code'),
    ('oop', 'Object-Oriented Programming', 'Programming paradigm'),
    ('django', 'Django', 'Python web framework'),
    ('flask', 'Flask', 'Lightweight Python web framework'),
    ('databases', 'Databases', 'Structured data storage'),
    ('sql', 'SQL', 'Query language for databases'),
    ('git', 'Git', 'Version control system'),
    ('docker', 'Docker', 'Containerization platform'),
    ('api', 'APIs', 'Application Programming Interfaces'),
    ('javascript', 'JavaScript', 'Programming language for web'),
    ('html_css', 'HTML/CSS', 'Web page structure and styling'),
]

for skill_id, name, description in skills:
    client.query('CREATE (s:Skill {id: \$id, name: \$name, description: \$description})', 
        {'id': skill_id, 'name': name, 'description': description})

relationships = [
    ('variables', 'REQUIRES', 'python'),
    ('data_types', 'REQUIRES', 'python'),
    ('data_types', 'REQUIRES', 'variables'),
    ('functions', 'REQUIRES', 'python'),
    ('oop', 'REQUIRES', 'python'),
    ('oop', 'REQUIRES', 'functions'),
    ('django', 'REQUIRES', 'python'),
    ('django', 'REQUIRES', 'databases'),
    ('flask', 'REQUIRES', 'python'),
    ('flask', 'REQUIRES', 'databases'),
    ('api', 'REQUIRES', 'python'),
    ('sql', 'REQUIRES', 'databases'),
    ('docker', 'REQUIRES', 'git'),
    ('javascript', 'RELATED_TO', 'python'),
    ('html_css', 'RELATED_TO', 'javascript'),
]

for source_id, rel_type, target_id in relationships:
    client.query(f'MATCH (s:Skill {{id: \$source_id}}) MATCH (t:Skill {{id: \$target_id}}) CREATE (s)-[:{rel_type}]->(t)',
        {'source_id': source_id, 'target_id': target_id})

stats = client.get_graph_stats()
print(f'\\nSeeded: {stats[\"total_nodes\"]} nodes, {stats[\"total_relationships\"]} relationships')
client.close()
" 2>&1 | grep -v "Received notification" | grep -v "DEPRECATION" | grep -v "WARNING" | grep -v "position=" | grep -v "classification=" | grep -v "severity=" | grep -v "diagnostic_record=" | grep -v "gql_status=" | grep -v "status_description=" | grep -v "raw_classification=" | grep -v "raw_severity=" | grep -v "OPERATION=" | grep -v "OPERATION_CODE=" | grep -v "CURRENT_SCHEMA="
