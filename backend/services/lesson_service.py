"""
Lesson Service
Generate explanation + task for a KG node.
"""
from __future__ import annotations

import asyncio

from backend.config import config
from backend.llm.provider import get_llm


LESSON_TIMEOUT = config.llm.timeout_seconds


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

    prompt = (
        "You are a learning coach. Create a short lesson for the node below.\n"
        "Return JSON with keys: explanation, task.\n\n"
        f"Node name: {name}\n"
        f"Labels: {labels}\n"
        f"Description: {description}\n"
        f"Learning style: {learning_style or 'not specified'}\n"
        f"Instruction: {instruction}\n"
    )

    try:
        response = await asyncio.wait_for(llm.ainvoke([(\"human\", prompt)]), timeout=LESSON_TIMEOUT)
    except Exception as e:
        return {"error": f"Lesson generation failed: {e}"}

    content = str(response.content if hasattr(response, "content") else response)

    try:
        import json

        data = json.loads(content)
        return {
            "explanation": data.get("explanation", ""),
            "task": data.get("task", ""),
        }
    except Exception:
        return {
            "explanation": content.strip(),
            "task": "",
        }
