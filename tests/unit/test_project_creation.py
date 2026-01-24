import json

from backend.services.chat_service import ChatService


class DummyProjectDb:
    def __init__(self) -> None:
        self.summary = None
        self.chat_messages = None
        self.session_metadata = {}
        self.summary_nodes = []
        self.profile_nodes = []

    def upsert_project_summary(self, project_id: str, project_name: str, summary_json: str, is_default: bool = False) -> None:
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

    def update_chat_session_metadata(self, session_id: str, project_id: str, proposal_hash: str | None) -> None:
        self.session_metadata[session_id] = {
            "last_project_id": project_id,
            "last_proposal_hash": proposal_hash,
        }

    def upsert_project_nodes_from_summary(self, project_id: str, summary: dict) -> None:
        self.summary_nodes.append((project_id, summary))

    def upsert_project_profile_node(self, project_id: str, profile: dict) -> None:
        self.profile_nodes.append((project_id, profile))


def test_project_creation_persists_summary_and_chat_history():
    history = [
        {"role": "user", "content": "Hi!", "timestamp": "2024-01-01T00:00:00.000Z"},
        {
            "role": "assistant",
            "content": (
                "Tell me more about what you want to build so I can understand your goals."
            ),
            "timestamp": "2024-01-01T00:01:00.000Z",
        },
        {"role": "user", "content": "I want to explore Python lambdas.", "timestamp": "2024-01-01T00:02:00.000Z"},
    ]

    db = DummyProjectDb()
    service = ChatService(db=db)  # type: ignore[arg-type]

    summary = {
        "user_profile": {"interests": [], "skill_level": "", "time_available": "", "learning_style": ""},
        "agreed_project": {"name": "Deep Dive into Python Lambda Functions", "description": "", "timeline": "", "milestones": []},
        "topics": [],
        "skills": [],
        "concepts": [],
    }

    project_name, project_id = service._persist_project("session-123", summary, history, project_id="project-123")

    assert project_name == "Deep Dive into Python Lambda Functions"
    assert db.summary is not None
    assert db.summary["id"] == "project-123"
    assert db.summary["name"] == "Deep Dive into Python Lambda Functions"

    stored_summary = json.loads(db.summary["summary_json"])
    assert stored_summary["agreed_project"]["name"] == "Deep Dive into Python Lambda Functions"
    assert stored_summary["project_id"] == "project-123"
    assert stored_summary["session_id"] == "session-123"

    assert db.chat_messages is not None
    assert project_id == "project-123"
    assert len(db.chat_messages["messages"]) == 3
    assert db.chat_messages["messages"][0]["idx"] == 0
    assert db.chat_messages["messages"][2]["idx"] == 2
    assert db.session_metadata["session-123"]["last_project_id"] == "project-123"
