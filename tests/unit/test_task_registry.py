"""
Unit tests for TaskRegistry async tracking and cancellation.
"""
import asyncio

import pytest

from backend.services.task_registry import TaskRegistry


@pytest.mark.asyncio
async def test_task_registry_completes():
    registry = TaskRegistry()

    async def _work():
        return {"ok": True}

    job = registry.register("project-1", "lesson", _work())
    await asyncio.sleep(0.01)

    stored = registry.get(job.job_id)
    assert stored is not None
    assert stored.status == "completed"
    assert stored.result == {"ok": True}


@pytest.mark.asyncio
async def test_task_registry_cancel():
    registry = TaskRegistry()

    async def _work():
        await asyncio.sleep(1)
        return {"ok": True}

    job = registry.register("project-1", "assessment", _work())
    canceled = registry.cancel(job.job_id)
    assert canceled is True

    await asyncio.sleep(0.01)
    stored = registry.get(job.job_id)
    assert stored is not None
    assert stored.status in {"canceling", "canceled"}
