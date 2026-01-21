"""
Assessment Service
Generate and evaluate assessments for lessons.
"""
from __future__ import annotations

import asyncio
import json

from backend.config import config
from backend.llm.provider import get_llm


ASSESSMENT_TIMEOUT = config.llm.timeout_seconds


def _style_hint(style: str) -> str:
    style = (style or "").lower().strip()
    if style == "theoretical":
        return "Use a conceptual question and short written response."
    if style == "hands-on":
        return "Use a small practical task prompt."
    if style == "hybrid":
        return "Blend explanation with a small applied question."
    return "Use a short conceptual question."


async def generate_assessment(lesson: dict, profile: dict | None) -> dict:
    llm = get_llm()

    learning_style = (profile or {}).get("learning_style", "")
    prompt = (
        "Create one assessment prompt based on the lesson below.\n"
        "Return JSON with key: prompt.\n\n"
        f"Lesson explanation: {lesson.get('explanation', '')}\n"
        f"Lesson task: {lesson.get('task', '')}\n"
        f"Learning style: {learning_style or 'not specified'}\n"
        f"Instruction: {_style_hint(learning_style)}\n"
    )

    try:
        response = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=ASSESSMENT_TIMEOUT)
    except Exception as e:
        return {"error": f"Assessment generation failed: {e}"}

    content = str(response.content if hasattr(response, "content") else response)
    try:
        data = json.loads(content)
        return {"prompt": data.get("prompt", "").strip()}
    except Exception:
        return {"prompt": content.strip()}


async def evaluate_assessment(lesson: dict, assessment: dict, answer: str) -> dict:
    llm = get_llm()

    prompt = (
        "Evaluate the learner's answer. Return JSON with keys: result (pass|fail), feedback.\n\n"
        f"Lesson explanation: {lesson.get('explanation', '')}\n"
        f"Lesson task: {lesson.get('task', '')}\n"
        f"Assessment prompt: {assessment.get('prompt', '')}\n"
        f"Learner answer: {answer}\n"
    )

    try:
        response = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=ASSESSMENT_TIMEOUT)
    except Exception as e:
        return {"error": f"Assessment evaluation failed: {e}"}

    content = str(response.content if hasattr(response, "content") else response)
    try:
        data = json.loads(content)
        result = data.get("result", "").strip().lower()
        if result not in {"pass", "fail"}:
            result = "fail"
        return {"result": result, "feedback": data.get("feedback", "").strip()}
    except Exception:
        return {"result": "fail", "feedback": content.strip()}
