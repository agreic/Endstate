"""
Task registry for tracking async jobs and allowing cancellation.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable
from uuid import uuid4


@dataclass
class TaskInfo:
    job_id: str
    project_id: str
    kind: str
    status: str
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any] | None
    error: str | None
    meta: dict[str, Any]
    task: asyncio.Task


class TaskRegistry:
    """In-memory registry for async tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}

    def register(
        self,
        project_id: str,
        kind: str,
        coro: Awaitable[dict[str, Any] | None],
        meta: dict[str, Any] | None = None,
    ) -> TaskInfo:
        job_id = f"{kind}-{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        task = asyncio.create_task(coro)
        info = TaskInfo(
            job_id=job_id,
            project_id=project_id,
            kind=kind,
            status="running",
            created_at=now,
            updated_at=now,
            result=None,
            error=None,
            meta=meta or {},
            task=task,
        )
        self._tasks[job_id] = info
        task.add_done_callback(lambda t: self._handle_completion(job_id, t))
        return info

    def _handle_completion(self, job_id: str, task: asyncio.Task) -> None:
        if task.cancelled():
            self._update(job_id, status="canceled")
            return
        exc = task.exception()
        if exc:
            self._update(job_id, status="failed", error=str(exc))
            return
        self._update(job_id, status="completed", result=task.result())

    def _update(self, job_id: str, **kwargs: Any) -> None:
        info = self._tasks.get(job_id)
        if not info:
            return
        for key, value in kwargs.items():
            setattr(info, key, value)
        info.updated_at = datetime.now(timezone.utc)

    def get(self, job_id: str) -> TaskInfo | None:
        return self._tasks.get(job_id)

    def list_by_project(
        self,
        project_id: str,
        kind: str | None = None,
        node_id: str | None = None,
    ) -> list[TaskInfo]:
        results = []
        for info in self._tasks.values():
            if info.project_id != project_id:
                continue
            if kind and info.kind != kind:
                continue
            if node_id and info.meta.get("node_id") != node_id:
                continue
            results.append(info)
        return results

    def cancel(self, job_id: str) -> bool:
        info = self._tasks.get(job_id)
        if not info:
            return False
        if info.status in {"completed", "failed", "canceled"}:
            return False
        self._update(job_id, status="canceling")
        info.task.cancel()
        return True
