"""
Project Service
Helpers for preparing project data for KG extraction.
"""
from __future__ import annotations

import re
from typing import Any


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def build_project_extraction_text(
    summary: dict[str, Any],
    history: list[dict],
    max_messages: int = 10,
) -> str:
    agreed = summary.get("agreed_project", {}) if isinstance(summary.get("agreed_project"), dict) else {}
    header = [
        f"Project Name: {agreed.get('name', '')}",
        f"Description: {agreed.get('description', '')}",
        f"Timeline: {agreed.get('timeline', '')}",
        f"Milestones: {', '.join(agreed.get('milestones', []) or [])}",
    ]

    snippet = history[-max_messages:] if max_messages > 0 else history
    chat_lines = []
    for msg in snippet:
        role = msg.get("role", "user")
        content = _clean_text(str(msg.get("content", "")))
        if content:
            chat_lines.append(f"{role}: {content}")

    return "\n".join([line for line in header if line.strip()] + ["", "Chat History:"] + chat_lines)
