import asyncio
import json
from typing import Optional, Tuple

import pytest

from backend.services.chat_service import BackgroundTaskStore, ChatService


class DummyDb:
    def query(self, cypher: str, params: Optional[dict] = None) -> list[dict]:
        return []


def parse_sse(payload: str) -> Tuple[str, dict]:
    lines = [line for line in payload.splitlines() if line]
    event_line = next(line for line in lines if line.startswith("event: "))
    data_line = next(line for line in lines if line.startswith("data: "))
    event = event_line.replace("event: ", "")
    data = json.loads(data_line.replace("data: ", ""))
    return event, data


@pytest.mark.asyncio
async def test_event_stream_emits_message_metadata():
    session_id = "session-123"
    service = ChatService(db=DummyDb())
    messages = [
        {
            "role": "user",
            "content": "hello",
            "timestamp": "2024-01-01T00:00:00.000Z",
            "request_id": "req-1",
        }
    ]

    service.get_messages = lambda _session_id: messages  # type: ignore[assignment]
    service.is_locked = lambda _session_id: False  # type: ignore[assignment]

    stream = service.event_stream(session_id)

    try:
        initial_payload = await asyncio.wait_for(stream.__anext__(), timeout=1)
        event, data = parse_sse(initial_payload)
        assert event == "initial_messages"
        assert data["messages"] == messages
        assert data["locked"] is False

        await BackgroundTaskStore.notify(
            session_id,
            "message_added",
            {
                "role": "assistant",
                "content": "hi there",
                "timestamp": "2024-01-01T00:00:01.000Z",
                "request_id": "req-2",
            },
        )

        message_payload = await asyncio.wait_for(stream.__anext__(), timeout=1)
        event, data = parse_sse(message_payload)
        assert event == "message_added"
        assert data["content"] == "hi there"
        assert data["timestamp"] == "2024-01-01T00:00:01.000Z"
        assert data["request_id"] == "req-2"
    finally:
        await stream.aclose()


@pytest.mark.asyncio
async def test_locked_session_rejects_message():
    service = ChatService(db=DummyDb())
    service.is_locked = lambda _session_id: True  # type: ignore[assignment]

    response = await service.send_message("session-123", "Hello", "req-1")

    assert response.success is False
    assert response.is_processing is True


@pytest.mark.asyncio
async def test_project_persists_on_extraction_error():
    class DummyProjectDb(DummyDb):
        def __init__(self) -> None:
            self.summary = None
            self.chat_messages = None

        def upsert_project_summary(self, project_id: str, project_name: str, summary_json: str, is_default: bool = False) -> None:
            self.summary = {"id": project_id, "name": project_name, "summary_json": summary_json}

        def save_project_chat_history(self, project_id: str, messages: list[dict]) -> None:
            self.chat_messages = {"id": project_id, "messages": messages}

    history = [
        {"role": "assistant", "content": "Project: Deep Dive into Python Lambda Functions", "timestamp": "2024-01-01T00:01:00.000Z"},
        {"role": "user", "content": "I accept", "timestamp": "2024-01-01T00:02:00.000Z"},
    ]

    db = DummyProjectDb()
    service = ChatService(db=db)

    def _raise(_: list[dict]):
        raise RuntimeError("LLM failed")

    service._extract_summary_llm_with_invoke = _raise  # type: ignore[assignment]

    await service._extract_summary_async("session-err", [m.copy() for m in history])

    assert db.summary is not None
    assert db.summary["name"] == "Deep Dive into Python Lambda Functions"
    assert db.chat_messages is not None
