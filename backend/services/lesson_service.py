"""
Lesson Service
Generate explanation + task for a KG node.
"""
from __future__ import annotations

import asyncio

from backend.config import config
from backend.llm.provider import get_llm


LESSON_TIMEOUT = config.llm.timeout_seconds


def _extract_json_block(content: str) -> dict | None:
    try:
        import json
        import re

        fence_match = re.search(r"```json\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
        if fence_match:
            return json.loads(fence_match.group(1))

        obj_match = re.search(r"(\{.*\})", content, flags=re.DOTALL)
        if obj_match:
            return json.loads(obj_match.group(1))
    except Exception:
        return None
    return None


def parse_lesson_content(content: str) -> dict:
    data = _extract_json_block(content)
    if data:
        return {
            "explanation": data.get("explanation", ""),
            "task": data.get("task", ""),
        }

    cleaned = content.replace("```json", "").replace("```", "").strip()
    return {
        "explanation": cleaned,
        "task": "",
    }


def _style_instruction(style: str) -> str:
    style = (style or "").lower().strip()
    if style == "theoretical":
        return "Prefer a theoretical explanation and a reading/analysis task."
    if style == "hands-on":
        return "Prefer a practical coding or build task."
    if style == "hybrid":
        return "Provide a mix of explanation and a small practical task."
    return "Provide a balanced explanation and a simple task."


async def generate_lesson(node: dict, profile: dict | None) -> dict:
    llm = get_llm()

    name = node.get("properties", {}).get("name") or node.get("id")
    labels = ", ".join(node.get("labels", []))
    description = node.get("properties", {}).get("description", "")

    learning_style = (profile or {}).get("learning_style", "")
    instruction = _style_instruction(learning_style)

    skill_level = (profile or {}).get("skill_level", "intermediate")
    time_available = (profile or {}).get("time_available", "2 hours/week")

    prompt = (
        "You are a learning coach. Create a short lesson for the node below.\n"
        "Return JSON with keys: explanation, task.\n\n"
        f"Node name: {name}\n"
        f"Labels: {labels}\n"
        f"Description: {description}\n"
        f"Learning style: {learning_style or 'not specified'}\n"
        f"Skill level: {skill_level}\n"
        f"Time available: {time_available}\n"
        f"Instruction: {instruction}\n"
    )

    try:
        response = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=LESSON_TIMEOUT)
    except Exception as e:
        return {"error": f"Lesson generation failed: {e}"}

    content = str(response.content if hasattr(response, "content") else response)
    return parse_lesson_content(content)


async def generate_and_store_lesson(db, project_id: str, node: dict, profile: dict | None) -> dict:
    result = await generate_lesson(node, profile)
    if "error" in result:
        return result

    from uuid import uuid4

    lesson_id = f"lesson-{uuid4().hex[:8]}"
    title = node.get("properties", {}).get("name") or node.get("id")
    db.save_project_lesson(
        project_id,
        lesson_id,
        node.get("id"),
        title,
        result.get("explanation", ""),
        result.get("task", ""),
    )
    return {"lesson_id": lesson_id, **result}
