"""
Extraction Service - Handles background text extraction with cancellation support.

Provides:
- Idempotent extraction via request_id
- Background task cancellation
- Progress/status tracking
"""
import asyncio
import uuid
from dataclasses import dataclass
from typing import Optional

from backend.services.knowledge_graph import KnowledgeGraphService


EXTRACTION_TASKS: dict[str, dict] = {}


@dataclass
class ExtractionTask:
    """Represents an extraction task."""
    task_id: str
    request_id: str
    text: str
    status: str  # pending, running, complete, failed, cancelled
    result: Optional[dict] = None
    error: Optional[str] = None


def create_extraction_task(text: str, request_id: str) -> str:
    """Create a new extraction task."""
    task_id = str(uuid.uuid4())
    EXTRACTION_TASKS[task_id] = {
        "task_id": task_id,
        "request_id": request_id,
        "text": text,
        "status": "pending",
        "result": None,
        "error": None,
    }
    return task_id


def get_task(task_id: str) -> Optional[ExtractionTask]:
    """Get a task by ID."""
    if task_id not in EXTRACTION_TASKS:
        return None
    data = EXTRACTION_TASKS[task_id]
    return ExtractionTask(**data)


def cancel_task(task_id: str) -> bool:
    """Cancel a running task."""
    if task_id in EXTRACTION_TASKS:
        EXTRACTION_TASKS[task_id]["status"] = "cancelled"
        return True
    return False


async def run_extraction(task_id: str) -> None:
    """Run extraction in background."""
    if task_id not in EXTRACTION_TASKS:
        return
    
    task_data = EXTRACTION_TASKS[task_id]
    task_data["status"] = "running"
    
    try:
        service = KnowledgeGraphService()
        documents = service.extract_and_add(task_data["text"])
        
        if task_data["status"] == "cancelled":
            return
        
        task_data["status"] = "complete"
        task_data["result"] = {
            "message": "Extraction successful",
            "documents_count": len(documents),
        }
    except asyncio.CancelledError:
        task_data["status"] = "cancelled"
    except Exception as e:
        if task_data["status"] != "cancelled":
            task_data["status"] = "failed"
            task_data["error"] = str(e)


async def extract_text(text: str, request_id: str) -> dict:
    """
    Extract knowledge from text.
    
    Uses request_id for idempotency - same request_id returns cached result.
    """
    # Check for existing task with this request_id
    for task_id, task_data in EXTRACTION_TASKS.items():
        if task_data["request_id"] == request_id:
            if task_data["status"] == "complete":
                return task_data["result"]
            elif task_data["status"] in ("pending", "running"):
                return {"task_id": task_id, "status": task_data["status"]}
    
    # Create new task
    task_id = create_extraction_task(text, request_id)
    
    # Run extraction in background
    asyncio.create_task(run_extraction(task_id))
    
    return {"task_id": task_id, "status": "pending"}


def cleanup_old_tasks(max_age_seconds: int = 3600) -> int:
    """Remove old completed/cancelled tasks."""
    # TODO: Add timestamp tracking to tasks for proper cleanup
    # For now, tasks remain in memory until server restart
    return 0
