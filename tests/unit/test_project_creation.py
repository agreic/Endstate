import json

from backend.services.chat_service import ChatService


class DummyProjectDb:
    def __init__(self) -> None:
        self.summary = None
        self.chat_messages = None

    def upsert_project_summary(self, project_id: str, project_name: str, summary_json: str) -> None:
        self.summary = {
            "id": project_id,
            "name": project_name,
            "summary_json": summary_json,
        }

    def save_project_chat_history(self, project_id: str, messages: list[dict]) -> None:
        self.chat_messages = {
            "id": project_id,
            "messages": messages,
        }


def test_project_creation_persists_summary_and_chat_history():
    history = [
        {"role": "user", "content": "Hi!", "timestamp": "2024-01-01T00:00:00.000Z"},
        {
            "role": "assistant",
            "content": (
                "Excellent! Knowing you're comfortable with Python and prefer a theoretical approach with 2 hours per week, "
                "here's a project proposal focused on understanding Python lambdas:\n"
                "Project: Deep Dive into Python Lambda Functions\n"
                "* Goal: Gain a thorough theoretical understanding of Python's lambda functions.\n"
                "Do you accept this project proposal? If yes, type: I accept"
            ),
            "timestamp": "2024-01-01T00:01:00.000Z",
        },
        {"role": "user", "content": "I accept", "timestamp": "2024-01-01T00:02:00.000Z"},
    ]

    db = DummyProjectDb()
    service = ChatService(db=db)  # type: ignore[arg-type]

    summary = {
        "user_profile": {"interests": [], "skill_level": "", "time_available": "", "learning_style": ""},
        "agreed_project": {"name": "", "description": "", "timeline": "", "milestones": []},
        "topics": [],
        "skills": [],
        "concepts": [],
    }

    project_name = service._persist_project("session-123", summary, history)

    assert project_name == "Deep Dive into Python Lambda Functions"
    assert db.summary is not None
    assert db.summary["id"] == "session-123"
    assert db.summary["name"] == "Deep Dive into Python Lambda Functions"

    stored_summary = json.loads(db.summary["summary_json"])
    assert stored_summary["agreed_project"]["name"] == "Deep Dive into Python Lambda Functions"

    assert db.chat_messages is not None
    assert len(db.chat_messages["messages"]) == 3
    assert db.chat_messages["messages"][0]["idx"] == 0
    assert db.chat_messages["messages"][2]["idx"] == 2
