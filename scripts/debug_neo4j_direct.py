import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from backend.db.neo4j_client import Neo4jClient
from backend.config import config

def main():
    print("--- Neo4j Direct Inspection ---")
    print(f"Connecting to: {config.neo4j.uri}")
    
    try:
        # Use a generic client (session_id doesn't matter for this query as we inspect ALL)
        with Neo4jClient() as client:
            # Query to count total nodes
            total = client.query("MATCH (n) RETURN count(n) as count")
            print(f"\nTotal Nodes in DB: {total[0]['count']}")
            
            # Query to group by session_id
            print("\nNodes by Session ID:")
            sessions = client.query("""
                MATCH (n)
                RETURN n.session_id as session_id, count(n) as count, collect(distinct labels(n)) as labels
                ORDER BY count DESC
            """)
            
            if not sessions:
                print("  No nodes found with any session_id.")
            
            for row in sessions:
                sid = row.get('session_id', 'NULL')
                count = row.get('count')
                labels = row.get('labels')
                print(f"  - Session: '{sid}' | Count: {count} | Labels: {labels}")
                
            # Check specifically for Skill nodes
            print("\nSkill Nodes Details:")
            skills = client.query("""
                MATCH (s:Skill)
                RETURN s.id as id, s.name as name, s.session_id as session_id
                LIMIT 10
            """)
            for s in skills:
                print(f"  - [{s['session_id']}] {s['name']} ({s['id']})")
                
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
