"""
Project Service
Helpers for preparing project data for KG extraction.
"""
from __future__ import annotations

import re
from typing import Any


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _is_specified(value: str) -> bool:
    return bool(value and value.strip().lower() not in {"not specified", "not set", "unknown"})


def extract_profile_from_history(
    summary: dict[str, Any],
    history: list[dict],
) -> dict[str, Any]:
    profile = summary.get("user_profile")
    if not isinstance(profile, dict):
        profile = {}

    skill_level = profile.get("skill_level") or ""
    time_available = profile.get("time_available") or ""
    learning_style = profile.get("learning_style") or ""
    interests = profile.get("interests") if isinstance(profile.get("interests"), list) else []

    if not _is_specified(skill_level):
        skill_level = ""
    if not _is_specified(time_available):
        time_available = ""
    if not _is_specified(learning_style):
        learning_style = ""

    for msg in history:
        if msg.get("role") != "user":
            continue
        content = str(msg.get("content", "")).lower()

        if not skill_level:
            if "beginner" in content:
                skill_level = "beginner"
            elif "intermediate" in content:
                skill_level = "intermediate"
            elif "advanced" in content or "expert" in content:
                skill_level = "advanced"
            elif "comfortable" in content:
                skill_level = "intermediate"

        if not learning_style:
            if "theoretical" in content:
                learning_style = "theoretical"
            elif "hands-on" in content or "hands on" in content or "coding" in content:
                learning_style = "hands-on"
            elif "hybrid" in content or "mix" in content or "mixed" in content:
                learning_style = "hybrid"

        if not time_available:
            match = re.search(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?)", content)
            if match:
                hours = match.group(1)
                if "week" in content or "wk" in content:
                    time_available = f"{hours} hours/week"
                else:
                    time_available = f"{hours} hours"

        if not interests:
            learn_match = re.search(r"learn(?: about)?\s+(.+)", content)
            if learn_match:
                interests = [_clean_text(learn_match.group(1))]

    project_name = summary.get("agreed_project", {}).get("name")
    if not interests and project_name:
        interests = [project_name]

    topics = summary.get("topics") if isinstance(summary.get("topics"), list) else []
    interests = [i for i in interests + topics if i]
    profile["interests"] = list(dict.fromkeys(interests))
    profile["skill_level"] = skill_level or "not specified"
    profile["time_available"] = time_available or "not specified"
    profile["learning_style"] = learning_style or "not specified"
    return profile


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
