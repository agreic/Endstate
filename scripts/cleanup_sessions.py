
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.db.neo4j_client import Neo4jClient
from backend.config import config

def cleanup_sessions(hours: int = 24):
    """
    Cleanup sessions created more than `hours` ago and all their associated nodes.
    """
    print(f"Cleaning up sessions older than {hours} hours...")
    
    client = Neo4jClient()
    
    try:
        # Find old sessions
        query = f"""
        MATCH (s:ChatSession)
        WHERE s.created_at < datetime() - duration('PT{hours}H')
        RETURN s.id as session_id, s.created_at as created_at
        """
        
        # We need to run this with a dummy session_id because query() requires it or injects from context
        # But here we want global query.
        # Neo4jClient.query uses config.session_id if not present.
        # But the query above matches ALL sessions regardless of current session_id?
        # No, query method does NOT scope unless we add `WHERE n.session_id = ...`.
        # The query above searches ALL ChatSession nodes.
        
        results = client.query(query, {"session_id": "system-cleanup"}) # passing dummy session_id to satisfy injector
        
        print(f"Found {len(results)} old sessions.")
        
        deleted_count = 0
        for row in results:
            session_id = row["session_id"]
            print(f"Deleting session: {session_id} (created: {row['created_at']})")
            
            # Delete everything with this session_id
            # We can use the client's query method, but we need to ensure we delete by session_id property
            
            delete_query = """
            MATCH (n) 
            WHERE n.session_id = $target_session_id
            DETACH DELETE n
            """
            client.query(delete_query, {"target_session_id": session_id, "session_id": "system-cleanup"})
            
            # Also ensure the ChatSession node itself is deleted if it didn't have session_id property (it might not?)
            # ChatSession usually has id.
            client.query("MATCH (s:ChatSession {id: $target_session_id}) DETACH DELETE s", 
                         {"target_session_id": session_id, "session_id": "system-cleanup"})
                         
            deleted_count += 1
            
        print(f"Cleanup complete. Deleted {deleted_count} sessions.")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cleanup old sessions")
    parser.add_argument("--hours", type=int, default=24, help="Delete sessions older than N hours")
    args = parser.parse_args()
    
    cleanup_sessions(args.hours)
