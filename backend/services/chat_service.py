"""
Chat Service - Handles chat sessions, message processing, and real-time updates.

This module provides the core chat functionality with:
- Request idempotency via request_id
- SSE for real-time message updates
- Background task management with cancellation
- Separation of chat storage from knowledge graph
"""
import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Optional, AsyncGenerator, Callable, Any

from backend.config import config
from backend.db.neo4j_client import Neo4jClient
from backend.llm.provider import get_llm
from backend.services.agent_prompts import get_chat_system_prompt, get_project_suggestion_prompt
from backend.services.evaluation_service import evaluate_project_alignment, evaluate_kg_quality
from backend.services.opik_client import log_metric


LLM_TIMEOUT = config.llm.timeout_seconds  # seconds for LLM calls
HISTORY_MAX_MESSAGES = config.chat.history_max_messages
LOG_CHAT_TIMINGS = os.getenv("LOG_CHAT_TIMINGS", "false").lower() == "true"


def with_timeout(seconds: float):
    """Decorator to add timeout to async functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Operation timed out after {seconds}s")
        return wrapper
    return decorator


class AsyncTimeoutError(Exception):
    """Custom exception for timeout errors."""
    pass


def safe_run_with_timeout(func: Callable, timeout: float = LLM_TIMEOUT) -> Any:
    """
    Run a blocking function with timeout in a thread pool.
    
    Args:
        func: The blocking function to run
        timeout: Timeout in seconds
        
    Returns:
        Result of the function
        
    Raises:
        AsyncTimeoutError: If the function times out
    """
    loop = asyncio.get_event_loop()
    try:
        return loop.run_in_executor(None, func), timeout
    except Exception:
        return None, timeout


DEFAULT_PROFILE = {
    "interests": [],
    "skill_level": "intermediate",
    "time_available": "2 hours/week",
    "learning_style": "hybrid",
}


@dataclass
class ChatMessage:
    """Represents a chat message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


@dataclass
class ChatResponse:
    """Response from sending a message."""
    success: bool
    content: Optional[str] = None
    already_processed: bool = False
    is_processing: bool = False


class BackgroundTaskStore:
    """Stores background tasks for cancellation."""
    _tasks: dict[str, asyncio.Task] = {}
    _subscribers: dict[str, set[asyncio.Queue]] = {}
    
    @classmethod
    def has_task(cls, session_id: str) -> bool:
        return session_id in cls._tasks

    @classmethod
    def store(cls, session_id: str, task: asyncio.Task):
        cls._tasks[session_id] = task
    
    @classmethod
    def cancel(cls, session_id: str):
        if session_id in cls._tasks:
            cls._tasks[session_id].cancel()
            del cls._tasks[session_id]
    
    @classmethod
    async def cancel_all(cls):
        for task in cls._tasks.values():
            task.cancel()
        cls._tasks.clear()
    
    @classmethod
    def subscribe(cls, session_id: str, queue: asyncio.Queue):
        if session_id not in cls._subscribers:
            cls._subscribers[session_id] = set()
        cls._subscribers[session_id].add(queue)
    
    @classmethod
    def unsubscribe(cls, session_id: str, queue: asyncio.Queue):
        if session_id in cls._subscribers:
            cls._subscribers[session_id].discard(queue)
    
    @classmethod
    async def notify(cls, session_id: str, event: str, data: dict):
        if session_id in cls._subscribers:
            await asyncio.gather(
                *[q.put({"event": event, **data}) for q in cls._subscribers[session_id]],
                return_exceptions=True
            )


class ChatService:
    """Service for managing chat sessions and messages."""
    
    def __init__(self, db: Optional[Neo4jClient] = None):
        self._db = db
        self._llm = None
        self._cancelled_requests: set[str] = set()
    
    @property
    def db(self) -> Neo4jClient:
        if self._db is None:
            from backend.db.neo4j_client import Neo4jClient
            self._db = Neo4jClient()
        return self._db
    
    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
    
    def create_session(self, session_id: str) -> None:
        """Create a chat session if it doesn't exist."""
        self.db.query(
            "MERGE (s:ChatSession {id: $session_id}) SET s.created_at = datetime()",
            {"session_id": session_id}
        )
    
    def message_exists(self, session_id: str, request_id: str) -> bool:
        """Check if a message with this request_id already exists."""
        result = self.db.query(
            """
            MATCH (s:ChatSession {id: $session_id})-[:HAS_MESSAGE]->(m:ChatMessage {request_id: $request_id})
            RETURN count(m) as count
            """,
            {"session_id": session_id, "request_id": request_id}
        )
        return result[0].get("count", 0) > 0 if result else False
    
    def add_message(self, session_id: str, role: str, content: str, request_id: Optional[str] = None) -> dict:
        """Add a message to a chat session and return its payload."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.db.query(
            """
            MATCH (s:ChatSession {id: $session_id})
            CREATE (m:ChatMessage {
                role: $role,
                content: $content,
                timestamp: datetime($timestamp),
                request_id: $request_id
            })
            CREATE (s)-[:HAS_MESSAGE]->(m)
            """,
            {
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": timestamp,
                "request_id": request_id,
            }
        )
        return {
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "request_id": request_id,
        }
    
    def get_messages(self, session_id: str) -> list[dict]:
        """Get all messages for a session."""
        result = self.db.query(
            """
            MATCH (s:ChatSession {id: $session_id})-[:HAS_MESSAGE]->(m:ChatMessage)
            RETURN m.role as role, m.content as content, m.timestamp as timestamp, m.request_id as request_id
            ORDER BY m.timestamp
            """,
            {"session_id": session_id}
        )
        
        # Convert Neo4j DateTime to ISO string and handle missing request_id
        messages = []
        for msg in result:
            msg_copy = {
                "role": msg.get("role"),
                "content": msg.get("content"),
                "timestamp": None,
                "request_id": msg.get("request_id"),
            }
            timestamp = msg.get("timestamp")
            if timestamp:
                try:
                    # Neo4j DateTime to ISO string
                    msg_copy["timestamp"] = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                except Exception:
                    msg_copy["timestamp"] = None
            messages.append(msg_copy)
        
        return messages
    
    def set_locked(self, session_id: str, locked: bool) -> None:
        """Set the processing lock state."""
        self.db.query(
            "MATCH (s:ChatSession {id: $session_id}) SET s.is_processing = $locked",
            {"session_id": session_id, "locked": locked}
        )
    
    def is_locked(self, session_id: str) -> bool:
        """Check if session is locked."""
        result = self.db.query(
            "MATCH (s:ChatSession {id: $session_id}) RETURN COALESCE(s.is_processing, false) as locked",
            {"session_id": session_id},
        )
        return result[0].get("locked", False) if result else False

    def get_pending_proposals(self, session_id: str) -> list[dict]:
        """Return pending proposals for a chat session."""
        return self.db.get_pending_proposals(session_id)

    def has_pending_proposals(self, session_id: str) -> bool:
        """Check if a chat session has pending proposals."""
        return bool(self.db.get_pending_proposals(session_id))

    def clear_pending_proposals(self, session_id: str) -> None:
        """Clear any pending proposals for a chat session."""
        self.db.clear_pending_proposals(session_id)
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        BackgroundTaskStore.cancel(session_id)
        self.db.query(
            "MATCH (s:ChatSession {id: $session_id}) DETACH DELETE s",
            {"session_id": session_id}
        )
    
    async def send_message(self, session_id: str, content: str, request_id: str) -> ChatResponse:
        """Send a message - idempotent by request_id."""
        if self.is_locked(session_id):
            return ChatResponse(success=False, is_processing=True)
        if self.has_pending_proposals(session_id):
            await BackgroundTaskStore.notify(session_id, "error", {
                "message": "Please select a project or reject all proposals before continuing the chat."
            })
            return ChatResponse(success=False, is_processing=True)
        self.create_session(session_id)
        
        # Check idempotency
        if self.message_exists(session_id, request_id):
            return ChatResponse(success=True, already_processed=True)
        
        # Add user message
        user_message = self.add_message(session_id, "user", content, request_id)
        
        # Notify subscribers of new user message
        await BackgroundTaskStore.notify(session_id, "message_added", user_message)
        
        # Normal chat response - set locked state during processing
        self.set_locked(session_id, True)
        await BackgroundTaskStore.notify(session_id, "processing_started", {"reason": "chat"})
        
        try:
            history = self.get_messages(session_id)
            if HISTORY_MAX_MESSAGES > 0 and len(history) > HISTORY_MAX_MESSAGES:
                history = history[-HISTORY_MAX_MESSAGES:]
            messages_list = [("system", get_chat_system_prompt())]
            for msg in history:
                messages_list.append(("human" if msg["role"] == "user" else "ai", msg["content"]))
            
            start_time = time.monotonic()
            try:
                response = await asyncio.wait_for(
                    self.llm.ainvoke(messages_list),
                    timeout=LLM_TIMEOUT,
                )
            except asyncio.TimeoutError:
                self._cancelled_requests.add(request_id)
                await BackgroundTaskStore.notify(session_id, "error", {
                    "message": "Request timed out. The AI is taking too long to respond. Please try again."
                })
                raise
            
            response_text = str(response.content if hasattr(response, 'content') else response)
            if LOG_CHAT_TIMINGS:
                elapsed = time.monotonic() - start_time
                print(f"[Chat] LLM response in {elapsed:.2f}s (messages={len(messages_list)})")
            
            if request_id in self._cancelled_requests:
                self._cancelled_requests.discard(request_id)
                return ChatResponse(success=False)
            
            assistant_message = self.add_message(session_id, "assistant", response_text)
            
            await BackgroundTaskStore.notify(session_id, "message_added", assistant_message)
            
            return ChatResponse(success=True, content=response_text)
        except Exception as e:
            await BackgroundTaskStore.notify(session_id, "error", {
                "message": f"An error occurred: {str(e)}"
            })
            raise
        finally:
            self.set_locked(session_id, False)
            await BackgroundTaskStore.notify(session_id, "processing_complete", {"reason": "chat"})
    
    def _parse_project_suggestions(self, content: str) -> list[dict]:
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data.get("projects") if isinstance(data.get("projects"), list) else []
        except Exception:
            pass
        try:
            import re
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    return data.get("projects") if isinstance(data.get("projects"), list) else []
        except Exception:
            return []
        return []

    def _normalize_project_suggestions(self, raw: list[dict]) -> list[dict]:
        normalized = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip()
            description = str(entry.get("description", "")).strip()
            if not name:
                continue
            normalized.append({
                "id": f"proposal-{uuid.uuid4().hex[:8]}",
                "name": name,
                "description": description,
                "timeline": str(entry.get("timeline", "")).strip(),
                "milestones": [m for m in entry.get("milestones", []) if isinstance(m, str) and m.strip()],
                "skills": [s for s in entry.get("skills", []) if isinstance(s, str) and s.strip()],
                "topics": [t for t in entry.get("topics", []) if isinstance(t, str) and t.strip()],
                "concepts": [c for c in entry.get("concepts", []) if isinstance(c, str) and c.strip()],
            })
        return normalized

    async def request_project_suggestions(self, session_id: str, count: int = 3) -> dict:
        """Generate project suggestions from chat history."""
        self.create_session(session_id)
        pending = self.db.get_pending_proposals(session_id)
        if pending:
            return {"status": "pending", "proposals": pending}
        if self.db.is_session_locked(session_id):
            return {"status": "busy"}
        if BackgroundTaskStore.has_task(session_id):
            return {"status": "busy"}

        history = self.get_messages(session_id)
        self.set_locked(session_id, True)
        await BackgroundTaskStore.notify(session_id, "processing_started", {"reason": "proposal"})

        task = asyncio.create_task(self._generate_project_suggestions(session_id, history, count))
        BackgroundTaskStore.store(session_id, task)
        return {"status": "queued"}

    async def _generate_project_suggestions(self, session_id: str, history: list[dict], count: int):
        """Generate project suggestions asynchronously."""
        try:
            prompt = get_project_suggestion_prompt(history, max_projects=count)
            response = await asyncio.wait_for(self.llm.ainvoke([("human", prompt)]), timeout=LLM_TIMEOUT)
            content = str(response.content if hasattr(response, "content") else response)
            proposals = self._normalize_project_suggestions(self._parse_project_suggestions(content))

            if not proposals:
                proposals = [{
                    "id": f"proposal-{uuid.uuid4().hex[:8]}",
                    "name": "Learning Project",
                    "description": "A focused learning project based on your goals.",
                    "timeline": "2-4 weeks",
                    "milestones": [],
                    "skills": [],
                    "topics": [],
                    "concepts": [],
                }]

            self.db.set_pending_proposals(session_id, proposals)
            await BackgroundTaskStore.notify(session_id, "proposals_updated", {"proposals": proposals})
        except asyncio.CancelledError:
            await BackgroundTaskStore.notify(session_id, "processing_cancelled", {})
            raise
        except Exception as e:
            await BackgroundTaskStore.notify(session_id, "error", {"message": f"Failed to suggest projects: {e}"})
        finally:
            self.set_locked(session_id, False)
            await BackgroundTaskStore.notify(session_id, "processing_complete", {"reason": "proposal"})
            if session_id in BackgroundTaskStore._tasks:
                del BackgroundTaskStore._tasks[session_id]

    def _build_summary_from_proposal(self, proposal: dict) -> dict:
        return {
            "user_profile": {**DEFAULT_PROFILE},
            "agreed_project": {
                "name": proposal.get("name", "Untitled Project"),
                "description": proposal.get("description", ""),
                "timeline": proposal.get("timeline", ""),
                "milestones": proposal.get("milestones", []) or [],
            },
            "topics": proposal.get("topics", []) or [],
            "skills": proposal.get("skills", []) or [],
            "concepts": proposal.get("concepts", []) or [],
        }

    async def accept_project_proposal(self, session_id: str, proposal_id: str) -> dict:
        """Accept a pending proposal and create a project."""
        proposals = self.db.get_pending_proposals(session_id)
        proposal = next((p for p in proposals if p.get("id") == proposal_id), None)
        if not proposal:
            raise ValueError("Proposal not found")

        history = self.get_messages(session_id)
        summary = self._build_summary_from_proposal(proposal)
        project_name, project_id = self._persist_project(session_id, summary, history)
        self.db.clear_pending_proposals(session_id)
        self.set_locked(session_id, False)

        message = f"Project saved: **{project_name}**. View it in the Projects tab."
        assistant_message = self.add_message(session_id, "assistant", message)
        return {"project_id": project_id, "project_name": project_name, "message": message, "assistant_message": assistant_message}

    async def reject_project_proposals(self, session_id: str) -> None:
        """Reject all pending proposals."""
        self.db.clear_pending_proposals(session_id)
        self.set_locked(session_id, False)

    def _persist_project(self, session_id: str, summary: dict, history: list[dict], project_id: str | None = None) -> tuple[str, str]:
        if "agreed_project" not in summary or not isinstance(summary.get("agreed_project"), dict):
            summary["agreed_project"] = {
                "name": "",
                "description": "",
                "timeline": "",
                "milestones": [],
            }
        project_name = summary.get("agreed_project", {}).get("name") or "Untitled Project"
        summary["agreed_project"]["name"] = project_name
        summary["user_profile"] = summary.get("user_profile") if isinstance(summary.get("user_profile"), dict) else {**DEFAULT_PROFILE}

        project_id = project_id or f"{session_id}-{uuid.uuid4().hex[:8]}"
        summary["project_id"] = project_id
        summary["session_id"] = session_id

        self.db.upsert_project_summary(project_id, project_name, json.dumps(summary))
        self.db.upsert_project_profile_node(project_id, summary.get("user_profile", {}))
        self.db.upsert_project_nodes_from_summary(project_id, summary)
        project_info = summary.get("agreed_project", {}) if isinstance(summary.get("agreed_project"), dict) else {}
        user_goal = ""
        for msg in history:
            if msg.get("role") == "user" and msg.get("content"):
                user_goal = str(msg.get("content"))
                break

        async def _log_alignment():
            result = await evaluate_project_alignment(user_goal, project_info)
            if "error" in result:
                return
            prompt_version = str(result.get("prompt_version", "unknown"))
            log_metric("project_alignment_score", float(result.get("score", 0.0)), session_id=project_id, tags=["alignment", prompt_version])

        async def _log_kg_quality():
            result = await evaluate_kg_quality(project_info, summary)
            if "error" in result:
                return
            prompt_version = str(result.get("prompt_version", "unknown"))
            log_metric("kg_coverage_score", float(result.get("coverage_score", 0.0)), session_id=project_id, tags=["kg", prompt_version])
            log_metric("kg_redundancy_score", float(result.get("redundancy_score", 0.0)), session_id=project_id, tags=["kg", prompt_version])

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            loop.create_task(_log_alignment())
            loop.create_task(_log_kg_quality())
        else:
            _log_alignment().close()
            _log_kg_quality().close()

        history_payload = []
        for idx, message in enumerate(history):
            history_payload.append({
                "role": message.get("role"),
                "content": message.get("content"),
                "timestamp": message.get("timestamp"),
                "request_id": message.get("request_id"),
                "idx": idx,
            })
        self.db.save_project_chat_history(project_id, history_payload)
        self.db.update_chat_session_metadata(session_id, project_id, None)
        return project_name, project_id
    
    async def event_stream(self, session_id: str) -> AsyncGenerator[str, None]:
        """Create an SSE event stream for a session with heartbeat."""
        queue: asyncio.Queue = asyncio.Queue()
        BackgroundTaskStore.subscribe(session_id, queue)
        HEARTBEAT_INTERVAL = 30  # seconds
        
        try:
            # Send initial messages (with error handling)
            try:
                messages = self.get_messages(session_id)
                proposals = self.db.get_pending_proposals(session_id)
                yield f"event: initial_messages\ndata: {json.dumps({'messages': messages, 'locked': self.is_locked(session_id), 'proposals': proposals, 'error': None})}\n\n"
            except Exception as e:
                print(f"[Chat] Error fetching initial messages: {e}")
                # Still send initial_messages with error - don't fail the stream
                yield f"event: initial_messages\ndata: {json.dumps({'messages': [], 'locked': False, 'proposals': [], 'error': 'Database unavailable. Chat will continue without history.'})}\n\n"
            
            last_heartbeat = asyncio.get_event_loop().time()
            while True:
                now = asyncio.get_event_loop().time()
                
                # Send heartbeat if needed
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    yield "event: heartbeat\ndata: {}\n\n"
                    last_heartbeat = now
                
                # Wait for events with timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
                    yield f"event: {event.get('event', 'message')}\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Continue loop to send heartbeat
                    pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[Chat] Event stream error: {e}")
            # Don't crash - just stop sending events
        finally:
            BackgroundTaskStore.unsubscribe(session_id, queue)


# Global service instance
chat_service = ChatService()
