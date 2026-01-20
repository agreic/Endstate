"""
Endstate API Server
FastAPI backend for the knowledge graph visualization, management, and chat interface.
"""
import json
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.services.knowledge_graph import KnowledgeGraphService
from backend.services.chat_service import chat_service


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    enable_web_search: bool = False


class ChatResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    already_processed: bool = False
    is_processing: bool = False


class DashboardStatsResponse(BaseModel):
    total_nodes: int
    total_relationships: int
    conversations: int = 0
    insights: int = 0


app = FastAPI(
    title="Endstate API",
    description="API for knowledge graph operations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service():
    """Create a KnowledgeGraphService instance."""
    return KnowledgeGraphService()


@app.get("/")
def root():
    """Root endpoint."""
    return {"status": "ok", "message": "Endstate API is running"}


@app.get("/api/health")
def health_check():
    """Check health of all services."""
    service = get_service()
    try:
        results = service.test_connection()
        return results
    except Exception as e:
        return {"database": False, "llm": False, "error": str(e)}
    finally:
        service.close()


@app.get("/api/graph")
def get_graph():
    """
    Fetch all nodes and relationships from the graph database.
    
    Returns:
        JSON with nodes and relationships arrays
    """
    service = get_service()
    try:
        nodes = service.get_nodes()
        relationships = service.get_relationships()
        
        return {
            "nodes": nodes,
            "relationships": relationships,
            "total_nodes": len(nodes),
            "total_relationships": len(relationships),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.get("/api/graph/stats")
def get_graph_stats():
    """Get graph statistics."""
    service = get_service()
    try:
        stats = service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.get("/api/nodes")
def get_nodes(label: Optional[str] = None, limit: int = 100):
    """Get nodes, optionally filtered by label."""
    service = get_service()
    try:
        nodes = service.get_nodes(label=label, limit=limit)
        return {"nodes": nodes, "count": len(nodes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.get("/api/relationships")
def get_relationships(limit: int = 100):
    """Get relationships from the graph."""
    service = get_service()
    try:
        relationships = service.get_relationships(limit=limit)
        return {"relationships": relationships, "count": len(relationships)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.post("/api/extract")
def extract_from_text(text: str):
    """
    Extract knowledge from text and add to graph.
    
    Args:
        text: Text to extract knowledge from
    
    Returns:
        Extracted documents info
    """
    service = get_service()
    try:
        documents = service.extract_and_add(text)
        return {
            "message": "Extraction successful",
            "documents_count": len(documents),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.post("/api/clean")
def clean_graph(label: Optional[str] = None):
    """Clean the graph, optionally by label."""
    service = get_service()
    try:
        if label:
            deleted = service.clean_by_label(label)
            return {"message": f"Deleted {deleted} nodes with label {label}"}
        else:
            service.clean()
            return {"message": "Graph cleaned successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.post("/api/merge")
def merge_duplicates(label: str, match_property: str = "id"):
    """
    Merge duplicate nodes.
    
    Args:
        label: Node label to merge
        match_property: Property to match on
    """
    service = get_service()
    try:
        merged = service.merge_duplicates(label, match_property)
        return {
            "message": f"Merged {merged} duplicate nodes",
            "merged_count": merged,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.get("/api/query")
def execute_query(cypher: str, params: Optional[str] = None):
    """
    Execute a custom Cypher query.
    
    Args:
        cypher: Cypher query string
        params: Optional JSON params (base64 encoded)
    """
    import base64
    
    service = get_service()
    try:
        query_params = {}
        if params:
            try:
                query_params = json.loads(base64.b64decode(params).decode())
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid params")
        
        result = service.query(cypher, query_params)
        return {"results": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.get("/api/stats/dashboard", response_model=DashboardStatsResponse)
def get_dashboard_stats():
    """Get statistics for the dashboard."""
    service = get_service()
    try:
        stats = service.get_stats()
        
        return {
            "total_nodes": stats.get("total_nodes", 0),
            "total_relationships": stats.get("total_relationships", 0),
            "conversations": 0,
            "insights": 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.post("/api/chat/{session_id}/messages")
async def send_chat_message(session_id: str, request: ChatRequest, http_request: Request):
    """
    Send a message in a persistent chat session.
    Uses request_id header for idempotency.
    """
    request_id = http_request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    
    response = await chat_service.send_message(session_id, request.message, request_id)
    
    if response.already_processed:
        return {"success": True, "already_processed": True}
    
    return {
        "success": True,
        "content": response.content,
        "is_processing": response.is_processing,
    }


@app.get("/api/chat/{session_id}/stream")
async def chat_event_stream(session_id: str):
    """Server-Sent Events stream for real-time chat updates."""
    async def event_generator():
        async for event in chat_service.event_stream(session_id):
            yield event
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/chat/{session_id}/messages")
def get_chat_messages(session_id: str):
    """Get all messages for a chat session."""
    messages = chat_service.get_messages(session_id)
    is_locked = chat_service.is_locked(session_id)
    return {"messages": messages, "is_locked": is_locked}


@app.post("/api/chat/{session_id}/reset")
async def reset_chat_session(session_id: str):
    """Reset a chat session and cancel any ongoing processing."""
    chat_service.delete_session(session_id)
    chat_service.create_session(session_id)
    return {"message": "Session reset", "session_id": session_id}


@app.delete("/api/chat/{session_id}")
def delete_chat_session(session_id: str):
    """Delete a chat session."""
    chat_service.delete_session(session_id)
    return {"message": "Session deleted"}


@app.get("/api/chat")
def list_chat_sessions():
    """List all chat sessions."""
    from backend.db.neo4j_client import Neo4jClient
    db = Neo4jClient()
    sessions = db.get_all_sessions()
    return {"sessions": sessions}


@app.delete("/api/graph/nodes/{node_id}")
def delete_node(node_id: str):
    """
    Delete a node and all its connected relationships.
    """
    service = get_service()
    try:
        result = service.db.delete_node(node_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/graph/relationships")
def delete_relationship(source_id: str, target_id: str, rel_type: str):
    """
    Delete a specific relationship between two nodes.
    """
    service = get_service()
    try:
        result = service.db.delete_relationship(source_id, target_id, rel_type)
        if not result.get("deleted"):
            raise HTTPException(status_code=404, detail="Relationship not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/node/{node_id}/connections")
def get_node_connections(node_id: str):
    """
    Get all connections for a node.
    """
    service = get_service()
    try:
        connections = service.db.get_connected_nodes(node_id)
        return {"node_id": node_id, "connections": connections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects")
def list_projects():
    """List all project summaries."""
    from pathlib import Path
    
    cache_dir = Path.home() / ".endstate" / "summaries"
    if not cache_dir.exists():
        return {"projects": []}
    
    projects = []
    for file_path in cache_dir.glob("*.json"):
        try:
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
                projects.append({
                    "id": data.get("session_id"),
                    "name": data.get("agreed_project", {}).get("name", "Untitled"),
                    "created_at": data.get("created_at"),
                    "interests": data.get("user_profile", {}).get("interests", []),
                })
        except Exception:
            continue
    
    return {"projects": sorted(projects, key=lambda x: x.get("created_at", ""), reverse=True)}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    """Get a specific project summary."""
    from pathlib import Path
    
    cache_dir = Path.home() / ".endstate" / "summaries"
    file_path = cache_dir / f"{project_id}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """Delete a project summary."""
    from pathlib import Path
    
    cache_dir = Path.home() / ".endstate" / "summaries"
    file_path = cache_dir / f"{project_id}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        file_path.unlink()
        return {"message": "Project deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
