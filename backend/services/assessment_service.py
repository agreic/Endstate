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


def parse_assessment_content(content: str) -> dict:
    data = _extract_json_block(content)
    if data:
        return data
    cleaned = content.replace("```json", "").replace("```", "").strip()
    return {"raw": cleaned}


async def generate_assessment(lesson: dict, profile: dict | None) -> dict:
    llm = get_llm()

    learning_style = (profile or {}).get("learning_style", "")
    prompt = (
        "Create one assessment prompt based on the lesson below.\n"
        "Return JSON with key: prompt.\n"
        "Use only the lesson content; do not invent new scope.\n\n"
        f"Lesson explanation: {lesson.get('explanation', '')}\n"
        f"Learning style: {learning_style or 'not specified'}\n"
        f"Instruction: {_style_hint(learning_style)}\n"
    )

    try:
        response = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=ASSESSMENT_TIMEOUT)
    except Exception as e:
        return {"error": f"Assessment generation failed: {e}"}

    content = str(response.content if hasattr(response, "content") else response)
    parsed = parse_assessment_content(content)
    if "prompt" in parsed:
        return {"prompt": str(parsed.get("prompt", "")).strip()}
    return {"prompt": str(parsed.get("raw", "")).strip()}


async def evaluate_assessment(lesson: dict, assessment: dict, answer: str) -> dict:
    llm = get_llm()

    prompt = (
        "Evaluate the learner's answer. Return JSON with keys: result (pass|fail), feedback.\n\n"
        f"Lesson explanation: {lesson.get('explanation', '')}\n"
        f"Assessment prompt: {assessment.get('prompt', '')}\n"
        f"Learner answer: {answer}\n"
    )

    try:
        response = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=ASSESSMENT_TIMEOUT)
    except Exception as e:
        return {"error": f"Assessment evaluation failed: {e}"}

    content = str(response.content if hasattr(response, "content") else response)
    parsed = parse_assessment_content(content)
    if "result" in parsed:
        result = str(parsed.get("result", "")).strip().lower()
        if result not in {"pass", "fail"}:
            result = "fail"
        return {"result": result, "feedback": str(parsed.get("feedback", "")).strip()}
    return {"result": "fail", "feedback": str(parsed.get("raw", "")).strip()}
