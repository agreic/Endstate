"""
Endstate API Server
FastAPI backend for the knowledge graph visualization, management, and chat interface.
"""
import asyncio
import json
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    summary_saved: bool = False
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
    """
    from backend.services.agent_prompts import get_chat_system_prompt
    
    service = get_service()
    try:
        if service.db.is_session_locked(session_id):
            raise HTTPException(status_code=423, detail="Session is processing. Please wait.")
        
        service.db.create_chat_session(session_id)
        service.db.add_chat_message(session_id, "user", request.message)
        
        llm = get_llm()
        history = service.db.get_chat_history(session_id)
        
        messages = [("system", get_chat_system_prompt())]
        for msg in history:
            messages.append(("human" if msg["role"] == "user" else "ai", msg["content"]))
        
        response_text = ""
        summary_saved = False
        is_processing = False
        
        user_message_lower = request.message.lower().strip()
        
        acceptance_patterns = [
            "i accept", "i agree", "yes, i accept", "yes i accept",
            "that sounds good", "sounds good", "sounds great",
            "let's do it", "lets do it", "yes please", "yes, please",
            "i agree to this", "accepted", "i'm in", "im in",
            "this looks good", "looks good", "perfect", "option 1", "option 2", "option 3"
        ]
        
        is_acceptance = any(pattern in user_message_lower for pattern in acceptance_patterns)
        
        if is_acceptance:
            has_summary, summary_data = extract_summary_fast(history)
            if has_summary and summary_data:
                service.db.set_session_locked(session_id, True)
                response_text = f"Excellent! I'm creating a detailed project plan for you: **{summary_data.get('agreed_project', {}).get('name', 'Untitled')}**. This will just a moment..."
                service.db.add_chat_message(session_id, "assistant", response_text)
                
                asyncio.create_task(extract_summary_async(session_id, history.copy()))
                
                return {
                    "content": response_text,
                    "sources": None,
                    "summary_saved": False,
                    "is_processing": True,
                }
            else:
                response_text = "I don't have a clear project proposal to accept yet. Let's continue discussing your goals."
        else:
            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
        
        service.db.add_chat_message(session_id, "assistant", str(response_text))
        
        return {
            "content": response_text,
            "sources": None,
            "summary_saved": summary_saved,
            "is_processing": is_processing,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def extract_summary_async(session_id: str, history: list[dict]):
    """Extract summary asynchronously in the background."""
    from backend.services.summary_cache import summary_cache
    
    try:
        has_llm_summary, llm_summary = extract_summary_llm(history)
        if has_llm_summary and llm_summary:
            if summary_cache.save(session_id, llm_summary):
                service = get_service()
                project_name = llm_summary.get('agreed_project', {}).get('name', 'Untitled')
                msg = f"Your detailed project plan is ready: **{project_name}**. View it in the Projects tab."
                service.db.add_chat_message(session_id, "assistant", msg)
        else:
            has_fast, fast_summary = extract_summary_fast(history)
            if has_fast and fast_summary:
                summary_cache.save(session_id, fast_summary)
    except Exception as e:
        print(f"Error extracting summary for session {session_id}: {e}")
    finally:
        try:
            service = get_service()
            service.db.set_session_locked(session_id, False)
        except Exception:
            pass


def extract_summary_llm(history: list[dict]) -> tuple[bool, dict | None]:
    """Extract summary using LLM for high-quality results."""
    from backend.llm.provider import get_llm
    
    user_msgs = [m for m in history if m["role"] == "user"]
    if len(user_msgs) < 3:
        return False, None
    
    last_assistant_msg = None
    for msg in reversed(history):
        if msg["role"] == "assistant":
            last_assistant_msg = msg["content"]
            break
    
    if not last_assistant_msg or "accept" not in last_assistant_msg.lower():
        return False, None
    
    prompt = """You are a learning project planner. Extract a structured project summary from the conversation.

Look for:
1. A project the user has agreed to
2. Their interests (list of 2+)
3. Skills to develop (list of 2+)
4. Topics to learn (list of 2+)
5. Timeline if mentioned
6. Milestones if mentioned

Output ONLY valid JSON:
{"user_profile": {"interests": [], "skill_level": "", "time_available": "", "learning_style": ""}, "agreed_project": {"name": "", "description": "", "timeline": "", "milestones": []}, "topics": [], "skills": [], "concepts": []}

If you cannot find all required fields, output: NOT_READY

Conversation:
"""
    
    for msg in history[-10:]:
        prompt += f"{msg['role']}: {msg['content']}\n"
    
    prompt += "\nOutput JSON only:"
    
    try:
        llm = get_llm()
        response = llm.invoke([("human", prompt)])
        content = str(response.content if hasattr(response, 'content') else response)
        
        if "NOT_READY" in content.upper():
            return False, None
        
        try:
            data = json.loads(content)
            return True, data
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[^{}]+\}', content)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return True, data
                except (json.JSONDecodeError, ValueError):
                    pass
            return False, None
    except Exception as e:
        print(f"LLM summary extraction error: {e}")
        return False, None


def extract_summary_fast(history: list[dict]) -> tuple[bool, dict]:
    """Fast summary extraction without extra LLM call."""
    user_msgs = [m for m in history if m["role"] == "user"]
    if len(user_msgs) < 3:
        return False, {}
    
    last_assistant = None
    for msg in reversed(history):
        if msg["role"] == "assistant":
            last_assistant = msg["content"]
            break
    
    if not last_assistant or "accept" not in last_assistant.lower():
        return False, {}
    
    interests = set()
    skills = set()
    topics = set()
    
    for msg in history[-8:]:
        content = msg.get("content", "").lower()
        if "machine learning" in content or "ml" in content:
            interests.add("machine learning")
        if "python" in content:
            topics.add("python")
        if "deep learning" in content or "neural network" in content:
            topics.add("deep learning")
        if "computer vision" in content:
            topics.add("computer vision")
        if "nlp" in content or "natural language" in content:
            topics.add("nlp")
        if "data" in content and "science" in content:
            interests.add("data science")
        if "web" in content and "develop" in content:
            interests.add("web development")
    
    if len(interests) == 0 and len(topics) == 0:
        return False, {}
    
    summary = {
        "user_profile": {
            "interests": list(interests)[:5],
            "skill_level": "not specified",
            "time_available": "not specified",
            "learning_style": "not specified"
        },
        "agreed_project": {
            "name": "Learning Project",
            "description": last_assistant.split("?")[0] + "?",
            "timeline": "2-4 weeks",
            "milestones": ["Set up environment", "Learn fundamentals", "Build project"]
        },
        "topics": list(topics)[:10],
        "skills": list(skills)[:10],
        "concepts": []
    }
    return True, summary


@app.get("/api/chat/{session_id}/messages")
def get_chat_history(session_id: str):
    """
    Get chat history for a session.
    """
    service = get_service()
    try:
        history = service.db.get_chat_history(session_id)
        is_locked = service.db.is_session_locked(session_id)
        return {"messages": history, "is_locked": is_locked}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/{session_id}/locked")
def check_session_locked(session_id: str):
    """Check if a chat session is locked (processing)."""
    service = get_service()
    try:
        locked = service.db.is_session_locked(session_id)
        return {"locked": locked}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat")
def list_chat_sessions():
    """List all chat sessions."""
    service = get_service()
    try:
        sessions = service.db.get_all_sessions()
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/{session_id}")
def delete_chat_session(session_id: str):
    """Delete a chat session and clear all messages."""
    service = get_service()
    try:
        service.db.delete_chat_session(session_id)
        return {"message": "Session deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/{session_id}/reset")
def reset_chat_session(session_id: str):
    """Reset a chat session by deleting it and creating a new one."""
    service = get_service()
    try:
        service.db.delete_chat_session(session_id)
        service.db.create_chat_session(session_id)
        return {"message": "Session reset", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    import json
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
