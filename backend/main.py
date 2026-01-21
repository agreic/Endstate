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
from backend.services.chat_service import chat_service, BackgroundTaskStore
from backend.services.extraction_service import cancel_task


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    enable_web_search: bool = False


class ExtractRequest(BaseModel):
    text: str


class ChatResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    already_processed: bool = False
    is_processing: bool = False


class ProjectRenameRequest(BaseModel):
    name: str


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


@app.get("/api/graph")
def get_graph():
    """
    Fetch all nodes and relationships from the graph database.
    Excludes chat-related nodes and relationships.
    
    Returns:
        JSON with nodes and relationships arrays
    """
    service = get_service()
    try:
        nodes = service.db.get_knowledge_graph_nodes()
        relationships = service.db.get_knowledge_graph_relationships()
        
        return {
            "nodes": nodes,
            "relationships": relationships,
            "total_nodes": len(nodes),
            "total_relationships": len(relationships),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/stats")
def get_graph_stats():
    """Get graph statistics for the knowledge graph (excluding chat nodes)."""
    service = get_service()
    try:
        stats = service.db.get_knowledge_graph_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nodes")
def get_nodes(label: Optional[str] = None, limit: int = 100):
    """Get nodes, optionally filtered by label."""
    service = get_service()
    try:
        nodes = service.get_nodes(label=label, limit=limit)
        return {"nodes": nodes, "count": len(nodes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/relationships")
def get_relationships(limit: int = 100):
    """Get relationships from the graph."""
    service = get_service()
    try:
        relationships = service.get_relationships(limit=limit)
        return {"relationships": relationships, "count": len(relationships)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract/sample")
def add_sample_data():
    """
    Add sample skill graph data to Neo4j.
    This creates proper nodes with correct types, bypassing LLM extraction.
    """
    from backend.db.neo4j_client import Neo4jClient
    from backend.config import Neo4jConfig
    
    config = Neo4jConfig()
    client = Neo4jClient(config)
    
    try:
        # Clean existing data
        client.clean_graph()
        
        # Create Skills
        skills = [
            ("python", "Python", "Programming language"),
            ("machine-learning", "Machine Learning", "AI subset that enables systems to learn from data"),
            ("deep-learning", "Deep Learning", "Uses neural networks with multiple layers"),
            ("tensorflow", "TensorFlow", "Open source ML framework by Google"),
            ("pytorch", "PyTorch", "Open source ML framework by Meta"),
            ("computer-vision", "Computer Vision", "Enables computers to see and understand images"),
            ("nlp", "Natural Language Processing", "Processes human language by computers"),
            ("neural-networks", "Neural Networks", "Computing systems inspired by biological brains"),
            ("llm", "Large Language Models", "Transformer-based models like GPT"),
        ]
        
        for skill_id, name, description in skills:
            client.query("""
                CREATE (s:Skill {
                    id: $id,
                    name: $name,
                    description: $description,
                    difficulty: 'intermediate',
                    importance: 'core'
                })
            """, {"id": skill_id, "name": name, "description": description})
        
        # Create relationships
        relationships = [
            ("machine-learning", "REQUIRES", "python"),
            ("deep-learning", "REQUIRES", "machine-learning"),
            ("tensorflow", "REQUIRES", "python"),
            ("tensorflow", "REQUIRES", "deep-learning"),
            ("pytorch", "REQUIRES", "python"),
            ("pytorch", "REQUIRES", "deep-learning"),
            ("computer-vision", "REQUIRES", "deep-learning"),
            ("nlp", "REQUIRES", "deep-learning"),
            ("neural-networks", "REQUIRES", "deep-learning"),
            ("llm", "REQUIRES", "neural-networks"),
            ("llm", "REQUIRES", "nlp"),
        ]
        
        for source_id, rel_type, target_id in relationships:
            client.query(f"""
                MATCH (s:Skill {{id: $source_id}})
                MATCH (t:Skill {{id: $target_id}})
                CREATE (s)-[:{rel_type} {{strength: 0.9}}]->(t)
            """, {"source_id": source_id, "target_id": target_id})
        
        # Get stats
        stats = client.get_graph_stats()
        
        return {
            "message": "Sample data added successfully",
            "total_nodes": stats.get("total_nodes", 0),
            "total_relationships": stats.get("total_relationships", 0),
        }
    finally:
        pass  # Don't close - let connection pool manage lifecycle


@app.post("/api/extract/cancel/{task_id}")
def cancel_extraction(task_id: str):
    """Cancel a running extraction task."""
    cancelled = cancel_task(task_id)
    return {"cancelled": cancelled}


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


@app.post("/api/chat/{session_id}/messages")
async def send_chat_message(session_id: str, request: ChatRequest, http_request: Request):
    """
    Send a message in a persistent chat session.
    Uses request_id header for idempotency.
    """
    try:
        request_id = http_request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        response = await chat_service.send_message(session_id, request.message, request_id)
        
        if response.is_processing:
            return {"success": False, "is_processing": True}

        if response.already_processed:
            return {"success": True, "already_processed": True}
        
        return {
            "success": True,
            "content": response.content,
            "is_processing": response.is_processing,
        }
    except Exception as e:
        print(f"[Chat] Error sending message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message. Please try again.")


@app.get("/api/chat/{session_id}/stream")
async def chat_event_stream(session_id: str):
    """Server-Sent Events stream for real-time chat updates."""
    async def event_generator():
        try:
            async for event in chat_service.event_stream(session_id):
                yield event
        except Exception as e:
            error_msg = str(e) if str(e) else "Connection error"
            yield f"event: error\ndata: {json.dumps({'message': error_msg})}\n\n"
    
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
    try:
        messages = chat_service.get_messages(session_id)
        is_locked = chat_service.is_locked(session_id)
        return {"messages": messages, "is_locked": is_locked}
    except Exception as e:
        print(f"[Chat] Error getting messages: {e}")
        return {"messages": [], "is_locked": False}


@app.post("/api/chat/{session_id}/reset")
async def reset_chat_session(session_id: str):
    """Reset a chat session and cancel any ongoing processing."""
    try:
        chat_service.delete_session(session_id)
        chat_service.create_session(session_id)
        
        # Notify all subscribers that session was reset
        await BackgroundTaskStore.notify(session_id, "session_reset", {
            "message": "Session reset",
        })
        
        return {"message": "Session reset", "session_id": session_id}
    except Exception as e:
        print(f"[Chat] Error resetting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset chat. Please try again.")


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
def list_projects(limit: int = 50):
    """List project summaries."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime

    db = Neo4jClient()
    records = db.list_project_summaries(limit=limit)

    projects = []
    for row in records:
        created_at = row.get("created_at")
        if isinstance(created_at, DateTime):
            created_at = created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        summary_json = row.get("summary_json") or "{}"
        try:
            data = json.loads(summary_json)
        except Exception:
            data = {}

        projects.append({
            "id": row.get("id"),
            "name": row.get("name") or data.get("agreed_project", {}).get("name", "Untitled"),
            "created_at": created_at,
            "interests": data.get("user_profile", {}).get("interests", []),
        })

    return {"projects": projects}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    """Get a specific project summary."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime

    db = Neo4jClient()
    records = db.get_project_summary(project_id)
    if not records:
        raise HTTPException(status_code=404, detail="Project not found")

    row = records[0]
    summary_json = row.get("summary_json") or "{}"
    try:
        data = json.loads(summary_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    created_at = row.get("created_at")
    if isinstance(created_at, DateTime):
        created_at = created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    updated_at = row.get("updated_at")
    if isinstance(updated_at, DateTime):
        updated_at = updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    data["session_id"] = row.get("id")
    data["created_at"] = created_at
    data["updated_at"] = updated_at
    return data


@app.patch("/api/projects/{project_id}/name")
def rename_project(project_id: str, request: ProjectRenameRequest):
    """Rename a project summary."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime

    new_name = request.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    db = Neo4jClient()
    records = db.get_project_summary(project_id)
    if not records:
        raise HTTPException(status_code=404, detail="Project not found")

    row = records[0]
    summary_json = row.get("summary_json") or "{}"
    try:
        data = json.loads(summary_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    agreed_project = data.get("agreed_project")
    if isinstance(agreed_project, dict):
        agreed_project["name"] = new_name
    else:
        data["agreed_project"] = {"name": new_name}

    updated_json = json.dumps(data)
    db.rename_project_summary(project_id, new_name, updated_json)

    updated_at = row.get("updated_at")
    if isinstance(updated_at, DateTime):
        updated_at = updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    return {"id": project_id, "name": new_name, "updated_at": updated_at}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """Delete a project summary."""
    from backend.db.neo4j_client import Neo4jClient

    db = Neo4jClient()
    records = db.get_project_summary(project_id)
    if not records:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        db.delete_project_summary(project_id)
        return {"message": "Project deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}/chat")
def get_project_chat(project_id: str):
    """Get chat history for a project."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime

    db = Neo4jClient()
    records = db.get_project_chat_history(project_id)
    if not records:
        raise HTTPException(status_code=404, detail="Chat history not found")

    messages = []
    for row in records:
        timestamp = row.get("timestamp")
        if isinstance(timestamp, DateTime):
            timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        messages.append({
            "role": row.get("role"),
            "content": row.get("content"),
            "timestamp": timestamp,
            "request_id": row.get("request_id"),
        })

    return {"messages": messages}


def main():
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
