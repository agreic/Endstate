"""
Endstate API Server
FastAPI backend for the knowledge graph visualization, management, and chat interface.
"""
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

from backend.config import Config
from backend.services.knowledge_graph import KnowledgeGraphService
from backend.llm.provider import get_llm


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    enable_web_search: bool = False


class ChatResponse(BaseModel):
    content: str
    sources: Optional[List[dict]] = None


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
    import json
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


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Send a chat message to the LLM.
    
    Args:
        request: Chat request with message, history, and web search option
        
    Returns:
        Chat response with content and optional sources
    """
    try:
        llm = get_llm()
        
        messages = []
        for msg in request.history:
            messages.append(("human" if msg.role == "user" else "ai", msg.content))
        messages.append(("human", request.message))
        
        response = llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        
        return {
            "content": content,
            "sources": None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/{session_id}/messages")
def send_chat_message(session_id: str, request: ChatRequest):
    """
    Send a message in a persistent chat session.
    
    Args:
        session_id: Chat session identifier
        request: Chat request with message and web search option
        
    Returns:
        Chat response with content and optional sources
    """
    service = get_service()
    try:
        service.db.create_chat_session(session_id)
        
        service.db.add_chat_message(session_id, "user", request.message)
        
        llm = get_llm()
        
        history = service.db.get_chat_history(session_id)
        messages = []
        for msg in history:
            messages.append(("human" if msg["role"] == "user" else "ai", msg["content"]))
        
        response = llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        
        service.db.add_chat_message(session_id, "assistant", str(content))
        
        return {
            "content": content,
            "sources": None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.get("/api/chat/{session_id}/messages")
def get_chat_history(session_id: str):
    """
    Get chat history for a session.
    
    Args:
        session_id: Chat session identifier
        
    Returns:
        List of chat messages
    """
    service = get_service()
    try:
        history = service.db.get_chat_history(session_id)
        return {"messages": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.get("/api/chat")
def list_chat_sessions():
    """List all chat sessions."""
    service = get_service()
    try:
        sessions = service.db.get_all_sessions()
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


@app.delete("/api/chat/{session_id}")
def delete_chat_session(session_id: str):
    """Delete a chat session."""
    service = get_service()
    try:
        service.db.delete_chat_session(session_id)
        return {"message": "Session deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        service.close()


def main():
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
