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
