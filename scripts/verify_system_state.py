import requests
import os
import json

BASE_URL = "http://localhost:8000/api"

def check_health():
    print("\n--- Health Check ---")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"Status: {r.status_code}")
        print(f"Body: {r.json()}")
    except Exception as e:
        print(f"Failed: {e}")

def check_graph_stats():
    print("\n--- Graph Stats ---")
    try:
        # Check without session header (default)
        r = requests.get(f"{BASE_URL}/graph/stats")
        print(f"Default Session Stats: {r.json()}")
    except Exception as e:
        print(f"Failed: {e}")

def list_sessions():
    print("\n--- Active Chat Sessions (from DB) ---")
    try:
        r = requests.get(f"{BASE_URL}/chat")
        sessions = r.json().get("sessions", [])
        print(f"Found {len(sessions)} sessions.")
        for s in sessions:
            print(f"  - {s['id']} (Msgs: {s['message_count']}, Created: {s['created_at']})")
        return sessions
    except Exception as e:
        print(f"Failed: {e}")
        return []

def main():
    check_health()
    check_graph_stats()
    sessions = list_sessions()
    
    if True: # Always run with a test session
        test_session = "test-session-verification"
        print(f"\n--- Testing with Session: {test_session} ---")
        headers = {"X-Session-ID": test_session}
        
        # 1. Trigger Add Sample Data
        print("Triggering Add Sample Data...")
        try:
            r = requests.post(f"{BASE_URL}/extract/sample", headers=headers)
            print(f"Add Sample Data Status: {r.status_code}")
            resp_data = r.json()
            print(f"Response: {resp_data}")
            if "debug_session_id" in resp_data:
                effective_session = resp_data['debug_session_id']
                print(f"DEBUG: Backend saw Session ID: {effective_session}")
                # Update headers to check the session where data was actually written
                headers = {"X-Session-ID": effective_session}
        except Exception as e:
            print(f"Add Sample Data Failed: {e}")
            
        # 2. Check Stats
        try:
            print(f"Checking graph for session: {headers.get('X-Session-ID')}")
            r = requests.get(f"{BASE_URL}/graph/stats", headers=headers)
            print(f"Stats: {r.json()}")
            
            r_graph = requests.get(f"{BASE_URL}/graph", headers=headers)
            data = r_graph.json()
            nodes_count = len(data.get('nodes', []))
            print(f"Nodes: {nodes_count}")
            print(f"Relationships: {len(data.get('relationships', []))}")
            
            if nodes_count > 0:
                print("SUCCESS: Nodes visible in graph.")
            else:
                print("FAILURE: No nodes visible after adding sample data.")
                
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    main()
