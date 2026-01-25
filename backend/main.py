"""
Endstate API Server
FastAPI backend for the knowledge graph visualization, management, and chat interface.
"""
import json
from datetime import datetime
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.services.knowledge_graph import KnowledgeGraphService
from backend.services.chat_service import chat_service, BackgroundTaskStore
from backend.services.extraction_service import cancel_task
from backend.services.project_service import build_project_extraction_text
from backend.schemas.skill_graph import SkillGraphSchema
from backend.services.lesson_service import generate_lesson, generate_and_store_lesson, parse_lesson_content
from backend.services.assessment_service import generate_assessment, evaluate_assessment, parse_assessment_content
from backend.services.evaluation_service import (
    build_project_brief,
    derive_required_skills,
    evaluate_submission,
)
from backend.services.task_registry import TaskRegistry
from backend.db.neo4j_client import DEFAULT_PROJECT_ID
from backend.config import (
    X_GEMINI_API_KEY,
    X_NEO4J_URI,
    X_NEO4J_USERNAME,
    X_NEO4J_PASSWORD,
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    enable_web_search: bool = False


class ExtractRequest(BaseModel):
    text: str


class ProjectSuggestionRequest(BaseModel):
    count: Optional[int] = 3


class ProjectOption(BaseModel):
    title: str = Field(description="Exciting name of the project")
    description: str = Field(description="2-3 sentence pitch")
    difficulty: str = Field(description="Beginner, Intermediate, or Advanced")
    tags: list[str] = Field(description="Key technologies or concepts")


class SuggestProjectsRequest(BaseModel):
    session_id: Optional[str] = None
    history: list[ChatMessage]
    count: Optional[int] = 3


class AcceptProjectOptionRequest(BaseModel):
    session_id: str
    option: ProjectOption


class ChatResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    already_processed: bool = False
    is_processing: bool = False


class ProjectRenameRequest(BaseModel):
    name: str


class LessonRequest(BaseModel):
    project_id: Optional[str] = None


class LessonGenerateRequest(BaseModel):
    node_id: str


class LessonMultiGenerateResponse(BaseModel):
    status: str
    jobs: list[dict]
    skipped: list[dict]


class ProfileUpdateRequest(BaseModel):
    interests: Optional[list[str]] = None
    skill_level: Optional[str] = None
    time_available: Optional[str] = None
    learning_style: Optional[str] = None


class AssessmentRequest(BaseModel):
    lesson_id: str


class AssessmentSubmission(BaseModel):
    answer: str


class CapstoneSubmissionRequest(BaseModel):
    content: str


ALLOWED_SKILL_LEVELS = {"beginner", "intermediate", "experienced", "advanced"}
ALLOWED_TIME = {
    "10 minutes/week",
    "30 minutes/week",
    "1 hour/week",
    "2 hours/week",
    "5 hours/week",
    "10 hours/week",
    "10+ hours/week",
}
ALLOWED_STYLE = {"theoretical", "hands-on", "hybrid"}


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

task_registry = TaskRegistry()


@app.middleware("http")
async def extract_config_headers(request: Request, call_next):
    """Extract configuration from headers and set in context variables."""
    # Extract headers
    gemini_key = request.headers.get("X-Gemini-API-Key")
    neo4j_uri = request.headers.get("X-Neo4j-URI")
    neo4j_user = request.headers.get("X-Neo4j-User")
    neo4j_password = request.headers.get("X-Neo4j-Password")

    # Set context variables and restore them after request
    tokens = []
    if gemini_key:
        tokens.append(X_GEMINI_API_KEY.set(gemini_key))
    if neo4j_uri:
        tokens.append(X_NEO4J_URI.set(neo4j_uri))
    if neo4j_user:
        tokens.append(X_NEO4J_USERNAME.set(neo4j_user))
    if neo4j_password:
        tokens.append(X_NEO4J_PASSWORD.set(neo4j_password))

    try:
        response = await call_next(request)
        return response
    finally:
        # Reset context variables (in reverse order)
        for token in reversed(tokens):
            if token.var == X_GEMINI_API_KEY:
                X_GEMINI_API_KEY.reset(token)
            elif token.var == X_NEO4J_URI:
                X_NEO4J_URI.reset(token)
            elif token.var == X_NEO4J_USERNAME:
                X_NEO4J_USERNAME.reset(token)
            elif token.var == X_NEO4J_PASSWORD:
                X_NEO4J_PASSWORD.reset(token)



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
        service.db.ensure_project_nodes()
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
        service.db.ensure_project_nodes()
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
        chat_service.clear_stale_lock(session_id)
        messages = chat_service.get_messages(session_id)
        is_locked = chat_service.is_locked(session_id)
        proposals = chat_service.get_pending_proposals(session_id)
        return {"messages": messages, "is_locked": is_locked, "proposals": proposals}
    except Exception as e:
        print(f"[Chat] Error getting messages: {e}")
        return {"messages": [], "is_locked": False, "proposals": []}


@app.get("/api/chat/{session_id}/proposals")
def get_chat_proposals(session_id: str):
    """Get pending project proposals for a chat session."""
    proposals = chat_service.get_pending_proposals(session_id)
    return {"proposals": proposals}


@app.post("/api/chat/{session_id}/proposals")
async def suggest_chat_projects(session_id: str, request: ProjectSuggestionRequest):
    """Generate project suggestions from chat history."""
    result = await chat_service.request_project_suggestions(session_id, count=request.count or 3)
    return result


@app.post("/api/suggest-projects")
async def suggest_projects(request: SuggestProjectsRequest):
    """Generate project suggestions from provided chat history."""
    if not request.history:
        raise HTTPException(status_code=400, detail="Chat history is required.")
    session_id = request.session_id or f"ad-hoc-{uuid.uuid4().hex[:8]}"
    history = [msg.model_dump() for msg in request.history]
    result = await chat_service.request_project_suggestions_from_history(
        session_id,
        history,
        count=request.count or 3,
    )
    if result.get("status") == "pending" and isinstance(result.get("proposals"), list):
        return {"status": "pending", "projects": [ProjectOption(**project).model_dump() for project in result["proposals"]]}
    return result


@app.post("/api/suggest-projects/accept")
async def accept_project_option(request: AcceptProjectOptionRequest):
    """Accept a suggested project option and create a project."""
    result = await chat_service.create_project_from_option(request.session_id, request.option.model_dump())
    await BackgroundTaskStore.notify(request.session_id, "proposals_cleared", {"proposals": []})
    return result


@app.post("/api/chat/{session_id}/proposals/reject")
async def reject_chat_projects(session_id: str):
    """Reject all pending project proposals."""
    await chat_service.reject_project_proposals(session_id)
    await BackgroundTaskStore.notify(session_id, "proposals_cleared", {"proposals": []})
    return {"status": "cleared"}


@app.post("/api/chat/{session_id}/proposals/{proposal_id}/accept")
async def accept_chat_project(session_id: str, proposal_id: str):
    """Accept a project proposal and create a project."""
    try:
        result = await chat_service.accept_project_proposal(session_id, proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await BackgroundTaskStore.notify(session_id, "message_added", result.get("assistant_message", {}))
    await BackgroundTaskStore.notify(session_id, "proposals_cleared", {"proposals": []})
    return {"project_id": result.get("project_id"), "project_name": result.get("project_name")}


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
    db.ensure_default_project()
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
    if project_id == DEFAULT_PROJECT_ID:
        db.ensure_default_project()
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
    data["is_default"] = bool(row.get("is_default")) if row.get("is_default") is not None else False
    return data


@app.patch("/api/projects/{project_id}/name")
def rename_project(project_id: str, request: ProjectRenameRequest):
    """Rename a project summary."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime

    new_name = request.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    if project_id == DEFAULT_PROJECT_ID:
        raise HTTPException(status_code=400, detail="Default project cannot be renamed")

    db = Neo4jClient()
    if project_id == DEFAULT_PROJECT_ID:
        db.ensure_default_project()
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
        if project_id == DEFAULT_PROJECT_ID:
            db.clear_project_content(project_id)
            return {"message": "Default project cleared"}
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


@app.get("/api/projects/{project_id}/nodes")
def get_project_nodes(project_id: str):
    """Get KG nodes connected to a project."""
    from backend.db.neo4j_client import Neo4jClient

    db = Neo4jClient()
    if project_id == DEFAULT_PROJECT_ID:
        db.ensure_default_project()
    return {"nodes": db.list_project_nodes(project_id)}


@app.patch("/api/projects/{project_id}/profile")
def update_project_profile(project_id: str, request: ProfileUpdateRequest):
    """Update project profile fields."""
    from backend.db.neo4j_client import Neo4jClient

    db = Neo4jClient()
    records = db.get_project_summary(project_id)
    if not records:
        raise HTTPException(status_code=404, detail="Project not found")

    summary_json = records[0].get("summary_json") or "{}"
    try:
        summary = json.loads(summary_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    profile = summary.get("user_profile")
    if not isinstance(profile, dict):
        profile = {}

    if request.interests is not None:
        profile["interests"] = request.interests
    if request.skill_level is not None:
        value = request.skill_level.lower()
        if value not in ALLOWED_SKILL_LEVELS:
            raise HTTPException(status_code=400, detail="Invalid skill level")
        profile["skill_level"] = value
    if request.time_available is not None:
        if request.time_available not in ALLOWED_TIME:
            raise HTTPException(status_code=400, detail="Invalid time commitment")
        profile["time_available"] = request.time_available
    if request.learning_style is not None:
        value = request.learning_style.lower()
        if value not in ALLOWED_STYLE:
            raise HTTPException(status_code=400, detail="Invalid learning style")
        profile["learning_style"] = value

    summary["user_profile"] = profile
    db.update_project_summary_json(project_id, json.dumps(summary))
    db.upsert_project_profile_node(project_id, profile)
    return {"project_id": project_id, "user_profile": profile}


@app.post("/api/graph/nodes/{node_id}/lesson")
async def generate_node_lesson(node_id: str, request: LessonRequest):
    """Generate a lesson for a KG node."""
    from backend.db.neo4j_client import Neo4jClient, _serialize_node

    db = Neo4jClient()
    node_result = db.get_node_by_id(node_id)
    if not node_result:
        raise HTTPException(status_code=404, detail="Node not found")

    node = _serialize_node(node_result.get("node"))
    profile = None

    if request.project_id:
        records = db.get_project_summary(request.project_id)
        if records:
            summary_json = records[0].get("summary_json") or "{}"
            try:
                summary = json.loads(summary_json)
                profile = summary.get("user_profile")
            except Exception:
                profile = None

    existing = db.list_project_lessons_for_node(request.project_id, node_id) if request.project_id else []
    lesson_index = len(existing) + 1
    prior_titles = [entry.get("title", "") for entry in existing[-3:]]
    result = await generate_lesson(node, profile, lesson_index, prior_titles)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    lesson_id = None
    if request.project_id:
        from uuid import uuid4

        lesson_id = f"lesson-{uuid4().hex[:8]}"
        title = node.get("properties", {}).get("name") or node_id
        db.save_project_lesson(
            request.project_id,
            lesson_id,
            node_id,
            title,
            result.get("explanation", ""),
            result.get("task", ""),
            lesson_index,
        )

    return {"node_id": node_id, "lesson_id": lesson_id, **result}


@app.post("/api/graph/nodes/{node_id}/lessons/generate")
async def generate_node_lessons(node_id: str):
    """Generate lessons for all projects connected to a KG node."""
    from backend.db.neo4j_client import Neo4jClient, _serialize_node
    from neo4j.time import DateTime

    db = Neo4jClient()
    db.ensure_default_project()
    node_result = db.get_node_by_id(node_id)
    if not node_result:
        raise HTTPException(status_code=404, detail="Node not found")

    node = _serialize_node(node_result.get("node"))
    node_name = node.get("properties", {}).get("name") or node_id

    project_rows = db.get_projects_for_node(node_id, node_name)
    projects = [row for row in project_rows if not row.get("is_default")]
    if not projects:
        projects = [{"id": DEFAULT_PROJECT_ID, "is_default": True}]

    jobs = []
    for project in projects:
        project_id = project.get("id")
        summary_records = db.get_project_summary(project_id)
        if not summary_records:
            continue
        existing = db.list_project_lessons_for_node(project_id, node_id)
        lesson_index = len(existing) + 1
        prior_titles = [entry.get("title", "") for entry in existing[-3:]]

        summary_json = summary_records[0].get("summary_json") or "{}"
        try:
            summary = json.loads(summary_json)
        except Exception:
            summary = {}
        profile = summary.get("user_profile")

        async def _task(
            project_id: str = project_id,
            profile: dict | None = profile,
            lesson_index: int = lesson_index,
            prior_titles: list[str] = prior_titles,
        ):
            result = await generate_and_store_lesson(db, project_id, node, profile, lesson_index, prior_titles)
            if "error" in result:
                raise RuntimeError(result["error"])
            return {"project_id": project_id, **result}

        job = task_registry.register(project_id, "lesson", _task(), meta={"node_id": node_id})
        jobs.append({"project_id": project_id, "job_id": job.job_id})

    return {"status": "queued", "jobs": jobs}


@app.post("/api/projects/{project_id}/lessons/generate")
async def queue_project_lesson(project_id: str, request: LessonGenerateRequest):
    """Queue lesson generation for a project node."""
    from backend.db.neo4j_client import Neo4jClient, _serialize_node
    from neo4j.time import DateTime

    db = Neo4jClient()
    if project_id == DEFAULT_PROJECT_ID:
        db.ensure_default_project()
    summary_records = db.get_project_summary(project_id)
    if not summary_records:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = db.list_project_lessons_for_node(project_id, request.node_id)
    lesson_index = len(existing) + 1
    prior_titles = [entry.get("title", "") for entry in existing[-3:]]

    node_result = db.get_node_by_id(request.node_id)
    if not node_result:
        raise HTTPException(status_code=404, detail="Node not found")

    summary_json = summary_records[0].get("summary_json") or "{}"
    try:
        summary = json.loads(summary_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    node = _serialize_node(node_result.get("node"))
    profile = summary.get("user_profile")

    async def _task():
        result = await generate_and_store_lesson(db, project_id, node, profile, lesson_index, prior_titles)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result

    job = task_registry.register(project_id, "lesson", _task(), meta={"node_id": request.node_id})

    return {"status": "queued", "job_id": job.job_id}


@app.get("/api/projects/{project_id}/lessons")
def list_project_lessons(project_id: str):
    """List stored lessons."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime

    db = Neo4jClient()
    if project_id == DEFAULT_PROJECT_ID:
        db.ensure_default_project()
    records = db.list_project_lessons(project_id)
    lessons = []
    for row in records:
        created_at = row.get("created_at")
        archived_at = row.get("archived_at")
        if isinstance(created_at, DateTime):
            created_at = created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if isinstance(archived_at, DateTime):
            archived_at = archived_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        explanation = row.get("explanation") or ""
        task = row.get("task") or ""
        if "```" in explanation or explanation.strip().startswith("{"):
            parsed = parse_lesson_content(explanation)
            explanation = parsed.get("explanation", explanation)
            task = parsed.get("task", task)
        lessons.append({
            "id": row.get("id"),
            "node_id": row.get("node_id"),
            "title": row.get("title"),
            "explanation": explanation,
            "task": task,
            "created_at": created_at,
            "archived": bool(row.get("archived")) if row.get("archived") is not None else False,
            "archived_at": archived_at,
        })
    return {"lessons": lessons}


@app.post("/api/projects/{project_id}/lessons/{lesson_id}/archive")
def archive_project_lesson(project_id: str, lesson_id: str):
    """Archive a lesson."""
    from backend.db.neo4j_client import Neo4jClient

    db = Neo4jClient()
    db.archive_project_lesson(project_id, lesson_id)
    return {"lesson_id": lesson_id, "archived": True}


@app.delete("/api/projects/{project_id}/lessons/{lesson_id}")
def delete_project_lesson(project_id: str, lesson_id: str):
    """Remove a lesson from a project."""
    from backend.db.neo4j_client import Neo4jClient

    db = Neo4jClient()
    db.delete_project_lesson(project_id, lesson_id)
    return {"lesson_id": lesson_id, "deleted": True}


@app.get("/api/projects/{project_id}/assessments")
def list_project_assessments(project_id: str):
    """List stored assessments."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime

    db = Neo4jClient()
    if project_id == DEFAULT_PROJECT_ID:
        db.ensure_default_project()
    records = db.list_project_assessments(project_id)
    assessments = []
    for row in records:
        created_at = row.get("created_at")
        updated_at = row.get("updated_at")
        archived_at = row.get("archived_at")
        if isinstance(created_at, DateTime):
            created_at = created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if isinstance(updated_at, DateTime):
            updated_at = updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if isinstance(archived_at, DateTime):
            archived_at = archived_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        prompt = row.get("prompt") or ""
        feedback = row.get("feedback") or ""
        if "```" in prompt or prompt.strip().startswith("{"):
            parsed_prompt = parse_assessment_content(prompt)
            prompt = parsed_prompt.get("prompt") or parsed_prompt.get("raw", prompt)
        if "```" in feedback or feedback.strip().startswith("{"):
            parsed_feedback = parse_assessment_content(feedback)
            feedback = parsed_feedback.get("feedback") or parsed_feedback.get("raw", feedback)
        assessments.append({
            "id": row.get("id"),
            "lesson_id": row.get("lesson_id"),
            "prompt": prompt,
            "status": row.get("status"),
            "feedback": feedback,
            "created_at": created_at,
            "updated_at": updated_at,
            "archived": bool(row.get("archived")) if row.get("archived") is not None else False,
            "archived_at": archived_at,
        })
    return {"assessments": assessments}


@app.post("/api/projects/{project_id}/assessments/{assessment_id}/archive")
def archive_project_assessment(project_id: str, assessment_id: str):
    """Archive an assessment."""
    from backend.db.neo4j_client import Neo4jClient

    db = Neo4jClient()
    db.archive_project_assessment(project_id, assessment_id)
    return {"assessment_id": assessment_id, "archived": True}


@app.delete("/api/projects/{project_id}/assessments/{assessment_id}")
def delete_project_assessment(project_id: str, assessment_id: str):
    """Remove an assessment from a project."""
    from backend.db.neo4j_client import Neo4jClient

    db = Neo4jClient()
    db.delete_project_assessment(project_id, assessment_id)
    return {"assessment_id": assessment_id, "deleted": True}


@app.post("/api/projects/{project_id}/submit")
async def submit_capstone(project_id: str, request: CapstoneSubmissionRequest):
    """Submit a capstone project for evaluation."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime
    from backend.config import config

    db = Neo4jClient()
    records = db.get_project_summary(project_id)
    if not records:
        raise HTTPException(status_code=404, detail="Project not found")

    summary_json = records[0].get("summary_json") or "{}"
    try:
        summary = json.loads(summary_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Submission content cannot be empty")

    attempt_number = db.get_project_submission_count(project_id) + 1
    submission_id = f"submission-{uuid.uuid4().hex[:8]}"
    db.create_project_submission(project_id, submission_id, request.content, attempt_number)

    skill_nodes = [
        node.get("properties", {}).get("name")
        for node in db.list_project_nodes(project_id)
        if "Skill" in (node.get("labels") or [])
    ]
    required_skills = derive_required_skills(summary, skill_nodes)
    project_brief = build_project_brief(summary)
    model_used = config.llm.provider

    async def _task():
        try:
            print(f"[CapstoneEval] task started submission_id={submission_id} project_id={project_id} skills={len(required_skills)}")
            result = await evaluate_submission(request.content, project_brief, required_skills, model_used)
            if "error" in result:
                db.update_submission_status(submission_id, "failed", feedback=str(result["error"]))
                return {"submission_id": submission_id, "error": result["error"]}
            raw_score = result.get("score")
            try:
                safe_score = float(raw_score) if raw_score is not None else 0.0
            except (TypeError, ValueError):
                safe_score = 0.0
            evaluation_id = f"eval-{uuid.uuid4().hex[:8]}"
            db.save_submission_evaluation(
                submission_id,
                evaluation_id,
                safe_score,
                result.get("criteria", {}),
                result.get("skill_evidence", {}),
                result.get("overall_feedback", ""),
                result.get("suggestions", []),
                bool(result.get("passed")),
                model_used,
                str(result.get("prompt_version", "")),
            )
            skill_evidence = result.get("skill_evidence", {}) if isinstance(result.get("skill_evidence"), dict) else {}
            if required_skills:
                covered = sum(1 for value in skill_evidence.values() if value and "missing" not in str(value).lower())
                coverage = covered / max(len(required_skills), 1)
            else:
                coverage = 1.0
            prompt_version = str(result.get("prompt_version", "unknown"))
            previous_score = None
            submissions = db.list_project_submissions(project_id)
            for submission in submissions:
                if submission.get("id") == submission_id:
                    continue
                score = submission.get("score")
                if score is not None:
                    try:
                        previous_score = float(score)
                        break
                    except (TypeError, ValueError):
                        continue
            if previous_score is not None:
                improvement = safe_score - previous_score
            capstone = summary.get("capstone") if isinstance(summary.get("capstone"), dict) else {}
            capstone.update({
                "last_submission_id": submission_id,
                "last_score": safe_score,
                "passed": bool(result.get("passed")),
                "attempts": attempt_number,
                "status": "completed" if result.get("passed") else "in_progress",
            })
            completed_at = None
            if result.get("passed"):
                completed_at = datetime.utcnow().isoformat()
                capstone["completed_at"] = completed_at
            summary["capstone"] = capstone
            db.update_project_summary_json(project_id, json.dumps(summary))
            db.update_project_capstone_state(
                project_id,
                capstone.get("status", "in_progress"),
                capstone.get("last_score", 0.0),
                completed_at,
            )
            return {"submission_id": submission_id, "evaluation_id": evaluation_id, **result}
        except Exception as exc:
            print(f"[CapstoneEval] task failed submission_id={submission_id} error={repr(exc)}")
            db.update_submission_status(submission_id, "failed", feedback=str(exc))
            raise

    job = task_registry.register(project_id, "capstone-eval", _task(), meta={"submission_id": submission_id})
    return {"status": "queued", "job_id": job.job_id, "submission_id": submission_id, "attempt": attempt_number}


@app.get("/api/projects/{project_id}/submissions")
def list_project_submissions(project_id: str):
    """List capstone submissions for a project."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime

    db = Neo4jClient()
    if project_id == DEFAULT_PROJECT_ID:
        return {"submissions": []}
    records = db.list_project_submissions(project_id)
    submissions = []
    for row in records:
        submitted_at = row.get("submitted_at")
        evaluated_at = row.get("evaluated_at")
        if isinstance(submitted_at, DateTime):
            submitted_at = submitted_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if isinstance(evaluated_at, DateTime):
            evaluated_at = evaluated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        submissions.append({
            "id": row.get("id"),
            "project_id": row.get("project_id"),
            "content": row.get("content"),
            "attempt_number": row.get("attempt_number"),
            "status": row.get("status"),
            "score": row.get("score"),
            "passed": bool(row.get("passed")) if row.get("passed") is not None else False,
            "feedback": row.get("feedback"),
            "submitted_at": submitted_at,
            "evaluated_at": evaluated_at,
        })
    return {"submissions": submissions}


@app.get("/api/submissions/{submission_id}")
def get_submission(submission_id: str):
    """Get submission with evaluations."""
    from backend.db.neo4j_client import Neo4jClient
    from neo4j.time import DateTime

    db = Neo4jClient()
    records = db.get_submission(submission_id)
    if not records:
        raise HTTPException(status_code=404, detail="Submission not found")

    row = records[0]
    submitted_at = row.get("submitted_at")
    evaluated_at = row.get("evaluated_at")
    if isinstance(submitted_at, DateTime):
        submitted_at = submitted_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(evaluated_at, DateTime):
        evaluated_at = evaluated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    evaluations = db.list_submission_evaluations(submission_id)
    formatted_evals = []
    for entry in evaluations:
        eval_at = entry.get("evaluated_at")
        if isinstance(eval_at, DateTime):
            eval_at = eval_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        rubric = entry.get("rubric")
        skill_evidence = entry.get("skill_evidence")
        if isinstance(rubric, str):
            try:
                rubric = json.loads(rubric)
            except Exception:
                rubric = {}
        if isinstance(skill_evidence, str):
            try:
                skill_evidence = json.loads(skill_evidence)
            except Exception:
                skill_evidence = {}
        formatted_evals.append({**entry, "evaluated_at": eval_at})
        formatted_evals[-1]["rubric"] = rubric
        formatted_evals[-1]["skill_evidence"] = skill_evidence

    return {
        "submission": {
            "id": row.get("id"),
            "project_id": row.get("project_id"),
            "content": row.get("content"),
            "attempt_number": row.get("attempt_number"),
            "status": row.get("status"),
            "score": row.get("score"),
            "passed": bool(row.get("passed")) if row.get("passed") is not None else False,
            "feedback": row.get("feedback"),
            "submitted_at": submitted_at,
            "evaluated_at": evaluated_at,
        },
        "evaluations": formatted_evals,
    }


@app.post("/api/projects/{project_id}/assessments")
async def create_project_assessment(project_id: str, request: AssessmentRequest):
    """Queue assessment generation for a lesson."""
    from backend.db.neo4j_client import Neo4jClient

    db = Neo4jClient()
    if project_id == DEFAULT_PROJECT_ID:
        db.ensure_default_project()
    summary_records = db.get_project_summary(project_id)
    if not summary_records:
        raise HTTPException(status_code=404, detail="Project not found")

    summary_json = summary_records[0].get("summary_json") or "{}"
    try:
        summary = json.loads(summary_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    lessons = db.list_project_lessons(project_id)
    lesson = next((l for l in lessons if l.get("id") == request.lesson_id), None)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    async def _task():
        result = await generate_assessment(lesson, summary.get("user_profile"))
        if "error" in result:
            raise RuntimeError(result["error"])
        from uuid import uuid4

        assessment_id = f"assessment-{uuid4().hex[:8]}"
        db.save_project_assessment(project_id, assessment_id, request.lesson_id, result.get("prompt", ""))
        return {"assessment_id": assessment_id, "prompt": result.get("prompt", "")}

    job = task_registry.register(project_id, "assessment", _task(), meta={"lesson_id": request.lesson_id})

    return {"status": "queued", "job_id": job.job_id}


@app.post("/api/projects/{project_id}/assessments/{assessment_id}/submit")
async def submit_project_assessment(project_id: str, assessment_id: str, request: AssessmentSubmission):
    """Submit an assessment answer for evaluation."""
    from backend.db.neo4j_client import Neo4jClient

    db = Neo4jClient()
    if project_id == DEFAULT_PROJECT_ID:
        db.ensure_default_project()
    summary_records = db.get_project_summary(project_id)
    if not summary_records:
        raise HTTPException(status_code=404, detail="Project not found")

    summary_json = summary_records[0].get("summary_json") or "{}"
    try:
        summary = json.loads(summary_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    assessments = db.list_project_assessments(project_id)
    assessment = next((a for a in assessments if a.get("id") == assessment_id), None)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    lessons = db.list_project_lessons(project_id)
    lesson = next((l for l in lessons if l.get("id") == assessment.get("lesson_id")), None)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    result = await evaluate_assessment(lesson, assessment, request.answer)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    status = result.get("result", "fail")
    archive_assessment = status == "pass"
    db.update_project_assessment(
        assessment_id,
        status,
        result.get("feedback", ""),
        request.answer,
        archived=archive_assessment,
    )
    if archive_assessment:
        db.archive_project_lesson(project_id, assessment.get("lesson_id"))

    return {"assessment_id": assessment_id, "result": status, "feedback": result.get("feedback")}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    """Check status for an async job."""
    job = task_registry.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "project_id": job.project_id,
        "kind": job.kind,
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "meta": job.meta,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


@app.delete("/api/jobs/{job_id}")
def cancel_job(job_id: str):
    """Cancel a queued or running job."""
    job = task_registry.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    canceled = task_registry.cancel(job_id)
    if not canceled:
        raise HTTPException(status_code=409, detail="Job cannot be canceled")
    return {
        "job_id": job_id,
        "status": job.status,
    }


@app.get("/api/projects/{project_id}/jobs")
def list_project_jobs(project_id: str, kind: Optional[str] = None, node_id: Optional[str] = None):
    """List active jobs for a project."""
    jobs = task_registry.list_by_project(project_id, kind=kind, node_id=node_id)
    return {
        "jobs": [
            {
                "job_id": job.job_id,
                "project_id": job.project_id,
                "kind": job.kind,
                "status": job.status,
                "meta": job.meta,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
            }
            for job in jobs
        ]
    }


@app.post("/api/projects/{project_id}/start")
async def start_project(project_id: str):
    """Reinitialize a project by extracting KG data from chat history."""
    from backend.db.neo4j_client import Neo4jClient

    if project_id == DEFAULT_PROJECT_ID:
        raise HTTPException(status_code=400, detail="Default project cannot be started")

    db = Neo4jClient()
    records = db.get_project_summary(project_id)
    if not records:
        raise HTTPException(status_code=404, detail="Project not found")

    async def _task():
        row = records[0]
        summary_json = row.get("summary_json") or "{}"
        try:
            summary = json.loads(summary_json)
        except Exception as e:
            raise RuntimeError(str(e))

        history = db.get_project_chat_history(project_id)
        if not history:
            history = []

        project_name = summary.get("agreed_project", {}).get("name") or row.get("name", "Untitled")
        db.upsert_project_summary(project_id, project_name, json.dumps(summary))
        db.upsert_project_profile_node(project_id, summary.get("user_profile", {}))
        db.upsert_project_nodes_from_summary(project_id, summary)

        text = build_project_extraction_text(summary, history)
        service = KnowledgeGraphService(schema=SkillGraphSchema)
        documents = await service.aextract(text)
        normalized = service.normalize_documents(documents)

        node_count = sum(len(doc.nodes) for doc in normalized)
        rel_count = sum(len(doc.relationships) for doc in normalized)
        if node_count == 0 and rel_count == 0:
            return {
                "message": "Project reinitialized (no new nodes extracted)",
                "project_id": project_id,
                "user_profile": summary.get("user_profile"),
                "nodes_added": 0,
                "relationships_added": 0,
                "project_status": summary.get("project_status"),
                "started_at": summary.get("started_at"),
            }

        db.clear_project_nodes(project_id)
        service.add_documents(normalized, normalize=False)

        graph_counts = db.get_project_graph_counts(project_id)
        node_count = graph_counts.get("nodes", 0)
        rel_count = graph_counts.get("relationships", 0)

        for label in ("Skill", "Concept", "Topic"):
            try:
                service.merge_duplicates(label, match_property="name")
            except Exception as e:
                print(f"[Projects] Merge duplicates failed for {label}: {e}")

        node_refs = []
        for doc in normalized:
            for node in doc.nodes:
                node_refs.append({"label": node.type, "name": node.properties.get("name")})
        db.connect_project_to_nodes(project_id, node_refs)
        summary_extra = db.upsert_project_nodes_from_summary(project_id, summary)
        graph_counts = db.get_project_graph_counts(project_id)
        node_count = graph_counts.get("nodes", 0)
        rel_count = graph_counts.get("relationships", 0)

        summary["project_status"] = "initialized"
        summary["started_at"] = datetime.utcnow().isoformat()
        db.upsert_project_summary(project_id, project_name, json.dumps(summary))

        return {
            "message": "Project reinitialized",
            "project_id": project_id,
            "user_profile": summary.get("user_profile"),
            "nodes_added": node_count,
            "relationships_added": rel_count,
            "project_status": summary.get("project_status"),
            "started_at": summary.get("started_at"),
        }

    job = task_registry.register(project_id, "project-reinit", _task(), meta={"project_id": project_id})
    return {"status": "queued", "job_id": job.job_id}


def main():
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
