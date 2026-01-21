"""
Project Migration Service
Migrates file-based summaries into Neo4j persistence.
"""
from pathlib import Path
from typing import Any

from backend.db.neo4j_client import Neo4jClient


def _load_json(path: Path) -> dict | None:
    try:
        import json

        with path.open("r") as handle:
            return json.load(handle)
    except Exception:
        return None


def migrate_file_summaries() -> dict[str, int]:
    """Migrate file-based summaries and chats into Neo4j, then remove files."""
    cache_dir = Path.home() / ".endstate" / "summaries"
    if not cache_dir.exists():
        return {"summaries": 0, "chats": 0, "deleted_files": 0}

    db = Neo4jClient()
    migrated_summaries = 0
    migrated_chats = 0
    deleted_files = 0

    for summary_path in cache_dir.glob("*.json"):
        if summary_path.name.endswith("_chat.json"):
            continue

        summary = _load_json(summary_path)
        if not summary:
            continue

        project_id = summary.get("session_id") or summary_path.stem
        project_name = summary.get("agreed_project", {}).get("name", "Untitled")

        try:
            import json

            db.upsert_project_summary(project_id, project_name, json.dumps(summary))
            migrated_summaries += 1
        except Exception:
            continue

        chat_path = cache_dir / f"{project_id}_chat.json"
        if chat_path.exists():
            chat_history = _load_json(chat_path) or []
            messages: list[dict[str, Any]] = []
            for idx, msg in enumerate(chat_history):
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp"),
                    "request_id": msg.get("request_id"),
                    "idx": idx,
                })
            try:
                db.save_project_chat_history(project_id, messages)
                migrated_chats += 1
            except Exception:
                pass

        try:
            summary_path.unlink()
            deleted_files += 1
        except Exception:
            pass

        if chat_path.exists():
            try:
                chat_path.unlink()
                deleted_files += 1
            except Exception:
                pass

    return {
        "summaries": migrated_summaries,
        "chats": migrated_chats,
        "deleted_files": deleted_files,
    }
