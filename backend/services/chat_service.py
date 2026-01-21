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
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Optional, AsyncGenerator, Callable, Any

from backend.config import config
from backend.db.neo4j_client import Neo4jClient
from backend.llm.provider import get_llm
from backend.services.agent_prompts import get_chat_system_prompt


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


ACCEPTANCE_START_MESSAGE = "Excellent! I'm creating a detailed project plan for you. This will take just a moment..."


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
            {"session_id": session_id}
        )
        return result[0].get("locked", False) if result else False
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        BackgroundTaskStore.cancel(session_id)
        self.db.query(
            "MATCH (s:ChatSession {id: $session_id}) DETACH DELETE s",
            {"session_id": session_id}
        )
    
    def _is_acceptance(self, message: str) -> bool:
        """Check if message indicates project acceptance."""
        lower = message.lower().strip()
        patterns = [
            "i accept", "i agree", "yes, i accept", "yes i accept",
            "that sounds good", "sounds good", "sounds great",
            "let's do it", "lets do it", "yes please", "yes, please",
            "i agree to this", "accepted", "i'm in", "im in",
            "this looks good", "looks good", "perfect", "option 1", "option 2", "option 3"
        ]
        return any(pattern in lower for pattern in patterns)
    
    async def send_message(self, session_id: str, content: str, request_id: str) -> ChatResponse:
        """Send a message - idempotent by request_id."""
        if self.is_locked(session_id):
            return ChatResponse(success=False, is_processing=True)
        self.create_session(session_id)
        
        # Check idempotency
        if self.message_exists(session_id, request_id):
            return ChatResponse(success=True, already_processed=True)
        
        # Add user message
        user_message = self.add_message(session_id, "user", content, request_id)
        
        # Notify subscribers of new user message
        await BackgroundTaskStore.notify(session_id, "message_added", user_message)
        
        # Check for acceptance
        if self._is_acceptance(content):
            return await self._handle_acceptance(session_id)
        
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
    
    async def _handle_acceptance(self, session_id: str) -> ChatResponse:
        """Handle project acceptance - start async extraction."""
        self.set_locked(session_id, True)

        history = self.get_messages(session_id)

        acceptance_message = self.add_message(session_id, "assistant", ACCEPTANCE_START_MESSAGE)
        await BackgroundTaskStore.notify(session_id, "message_added", acceptance_message)

        await BackgroundTaskStore.notify(session_id, "processing_started", {"reason": "summary"})

        task = asyncio.create_task(self._extract_summary_async(session_id, [m.copy() for m in history]))
        BackgroundTaskStore.store(session_id, task)
        
        return ChatResponse(success=True, content=ACCEPTANCE_START_MESSAGE, is_processing=True)
    
    async def _extract_summary_async(self, session_id: str, history: list[dict]):
        """Extract project summary asynchronously."""
        summary = None
        timeout_notice = None
        try:
            loop = asyncio.get_event_loop()
            try:
                has_llm, llm_summary = await asyncio.wait_for(
                    loop.run_in_executor(None, self._extract_summary_llm_with_invoke, history),
                    timeout=LLM_TIMEOUT
                )
            except asyncio.TimeoutError:
                has_llm = False
                llm_summary = None
                timeout_notice = "Project extraction timed out. The plan was saved with available details."

            if has_llm and llm_summary:
                summary = llm_summary
            else:
                has_fast, fast_summary = self._extract_summary_fast(history)
                if has_fast and fast_summary:
                    summary = fast_summary
        except asyncio.CancelledError:
            await BackgroundTaskStore.notify(session_id, "processing_cancelled", {})
            raise
        except Exception as e:
            print(f"Error extracting summary for session {session_id}: {e}")
        try:
            if summary is None:
                inferred_name = self._infer_project_name(history)
                summary = self._build_fallback_summary(history, inferred_name)

            project_name, _project_id = self._persist_project(session_id, summary, history)
            msg = f"Your detailed project plan is ready: **{project_name}**. View it in the Projects tab."
            ready_message = self.add_message(session_id, "assistant", msg)
            await BackgroundTaskStore.notify(session_id, "message_added", ready_message)

            if timeout_notice:
                await BackgroundTaskStore.notify(session_id, "error", {
                    "message": timeout_notice
                })
        except Exception as e:
            print(f"Error saving project for session {session_id}: {e}")
            await BackgroundTaskStore.notify(session_id, "error", {
                "message": "Failed to save the project. Please try again."
            })
        finally:
            self.set_locked(session_id, False)
            await BackgroundTaskStore.notify(session_id, "processing_complete", {})
            if session_id in BackgroundTaskStore._tasks:
                del BackgroundTaskStore._tasks[session_id]
    
    def _extract_summary_llm_with_invoke(self, history: list[dict]) -> tuple[bool, dict | None]:
        """Wrapper to call _extract_summary_llm in thread pool."""
        return self._extract_summary_llm(history)
    
    def _extract_summary_llm(self, history: list[dict]) -> tuple[bool, dict | None]:
        """Extract summary using LLM."""
        user_msgs = [m for m in history if m.get("role") == "user"]
        if len(user_msgs) < 3:
            return False, None
        
        last_assistant = None
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                last_assistant = msg.get("content", "")
                break
        
        if not last_assistant or "accept" not in last_assistant.lower():
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
            prompt += f"{msg.get('role', '')}: {msg.get('content', '')}\n"
        prompt += "\nOutput JSON only:"
        
        try:
            response = self.llm.invoke([("human", prompt)])
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
    
    def _extract_summary_fast(self, history: list[dict]) -> tuple[bool, dict]:
        """Fast summary extraction without LLM."""
        user_msgs = [m for m in history if m.get("role") == "user"]
        if len(user_msgs) < 3:
            return False, {}
        
        last_assistant = None
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                last_assistant = msg.get("content", "")
                break
        
        if not last_assistant or "accept" not in last_assistant.lower():
            return False, {}
        
        interests, skills, topics = set(), set(), set()
        
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
        
        if not interests and not topics:
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

    def _infer_project_name(self, history: list[dict]) -> str:
        acceptance_message = next((m for m in reversed(history) if m.get("role") == "user"), {})
        acceptance_text = str(acceptance_message.get("content", "")).strip()
        lower = acceptance_text.lower()

        match = re.search(r"accept\s+(?:option\s+)?(\d+)", lower)
        option_number = int(match.group(1)) if match else None

        if "accept" in lower:
            after = acceptance_text.split("accept", 1)[-1].strip(" :.-").strip()
            if after and not option_number:
                tokens = re.sub(r"[^a-z0-9\\s]", "", after.lower()).split()
                if tokens and all(tok in {"the", "a", "an", "one", "this", "that", "first", "second", "third"} for tok in tokens):
                    after = ""
                if after:
                    return after

        last_assistant = next((m for m in reversed(history) if m.get("role") == "assistant"), None)
        if last_assistant:
            content = str(last_assistant.get("content", ""))
            if option_number:
                for line in content.splitlines():
                    option_match = re.match(r"^\s*(\d+)\.\s*\**(.+?)\**\s*$", line.strip())
                    if option_match and int(option_match.group(1)) == option_number:
                        return option_match.group(2).strip()

            project_match = re.search(r"project\s*[:\-]\s*(.+)", content, flags=re.IGNORECASE)
            if project_match:
                return project_match.group(1).strip()

            bold_match = re.search(r"\*\*(.+?)\*\*", content)
            if bold_match:
                return bold_match.group(1).strip()

        return "Untitled Project"

    def _build_fallback_summary(self, history: list[dict], project_name: str) -> dict:
        return {
            "user_profile": {
                "interests": [],
                "skill_level": "not specified",
                "time_available": "not specified",
                "learning_style": "not specified",
            },
            "agreed_project": {
                "name": project_name,
                "description": "",
                "timeline": "",
                "milestones": [],
            },
            "topics": [],
            "skills": [],
            "concepts": [],
        }

    def _persist_project(self, session_id: str, summary: dict, history: list[dict], project_id: str | None = None) -> tuple[str, str]:
        if "agreed_project" not in summary or not isinstance(summary.get("agreed_project"), dict):
            summary["agreed_project"] = {
                "name": "",
                "description": "",
                "timeline": "",
                "milestones": [],
            }
        project_name = summary.get("agreed_project", {}).get("name") or self._infer_project_name(history)
        summary["agreed_project"]["name"] = project_name

        project_id = project_id or f"{session_id}-{uuid.uuid4().hex[:8]}"
        summary["project_id"] = project_id
        summary["session_id"] = session_id

        self.db.upsert_project_summary(project_id, project_name, json.dumps(summary))

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
                yield f"event: initial_messages\ndata: {json.dumps({'messages': messages, 'locked': self.is_locked(session_id), 'error': None})}\n\n"
            except Exception as e:
                print(f"[Chat] Error fetching initial messages: {e}")
                # Still send initial_messages with error - don't fail the stream
                yield f"event: initial_messages\ndata: {json.dumps({'messages': [], 'locked': False, 'error': 'Database unavailable. Chat will continue without history.'})}\n\n"
            
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
