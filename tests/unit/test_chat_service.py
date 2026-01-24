import asyncio
import json
from typing import Optional, Tuple

import pytest

from backend.services.chat_service import BackgroundTaskStore, ChatService


class DummyDb:
    def query(self, cypher: str, params: Optional[dict] = None) -> list[dict]:
        return []

    def get_chat_session_metadata(self, session_id: str) -> dict:
        return {}

    def get_pending_proposals(self, session_id: str) -> list[dict]:
        return []

    def clear_pending_proposals(self, session_id: str) -> None:
        return None

    def upsert_project_nodes_from_summary(self, project_id: str, summary: dict) -> None:
        return None


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
    service.db.get_pending_proposals = lambda _session_id: []  # type: ignore[assignment]

    stream = service.event_stream(session_id)

    try:
        initial_payload = await asyncio.wait_for(stream.__anext__(), timeout=1)
        event, data = parse_sse(initial_payload)
        assert event == "initial_messages"
        assert data["messages"] == messages
        assert data["locked"] is False
        assert data["proposals"] == []

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
async def test_pending_proposals_block_message():
    service = ChatService(db=DummyDb())
    service.has_pending_proposals = lambda _session_id: True  # type: ignore[assignment]

    response = await service.send_message("session-123", "Hello", "req-1")

    assert response.success is False
    assert response.is_processing is True
