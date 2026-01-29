"""
Lesson Service
Generate explanation + task for a KG node.
"""
from __future__ import annotations

import asyncio

from backend.config import config
from backend.llm.provider import get_llm
from backend.services.opik_client import trace, span
from .utils import extract_json, clean_markdown


LESSON_TIMEOUT = config.llm.timeout_seconds


# Removed _extract_json_block in favor of .utils.extract_json


def parse_lesson_content(content: str) -> dict:
    data = extract_json(content)
    if data and "explanation" in data:
        return {
            "explanation": str(data["explanation"]).strip(),
            "task": "",
        }

    # Fallback: if JSON failed or missing expected key, use the cleaned raw content
    cleaned = clean_markdown(content)
    
    # Heuristic: sometimes models return "explanation: ..." even if JSON fails
    lower_cleaned = cleaned.lower()
    if lower_cleaned.startswith("explanation:"):
        cleaned = cleaned[len("explanation:"):].strip()
    elif lower_cleaned.startswith("lesson:"):
        cleaned = cleaned[len("lesson:"):].strip()

    # Truncate if there are accidental task/assessment sections at the end
    import re
    cleaned = re.split(r"(?i)\n\s*(?:task|assessment|quiz|exercise):", cleaned, maxsplit=1)[0].strip()

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


def _display_name(node: dict) -> str:
    props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
    name = (props.get("name") or props.get("title") or "").strip()
    if name:
        return name
    labels = node.get("labels") or []
    if labels:
        return f"{labels[0]} topic"
    return "Untitled topic"


async def generate_lesson(
    node: dict,
    profile: dict | None,
    lesson_index: int,
    prior_titles: list[str],
) -> dict:
    llm = get_llm()
    model = getattr(getattr(config, "llm", None), "model", None) or getattr(getattr(config, "llm", None), "model_name", None) or "unknown"
    provider = getattr(getattr(config, "llm", None), "provider", None) or "openrouter"

    name = _display_name(node)
    labels = ", ".join(node.get("labels", []))
    description = node.get("properties", {}).get("description", "")

    learning_style = (profile or {}).get("learning_style", "")
    instruction = _style_instruction(learning_style)

    skill_level = (profile or {}).get("skill_level", "intermediate")
    time_available = (profile or {}).get("time_available", "2 hours/week")

    prior_section = ""
    if prior_titles:
        joined = "\n".join(f"- {title}" for title in prior_titles if title)
        prior_section = f"Previous lesson topics to avoid repeating:\n{joined}\n"

    prompt = (
        "You are a learning coach. Create a short, focused lesson for the node below.\n"
        "Return JSON with key: explanation.\n"
        "Keep it bite-sized (4-8 short paragraphs or bullets) and cover ONE specific aspect.\n"
        "Be concrete and specific to the topic; explain one subtopic in depth.\n"
        "Include at most one short, precise example (code or query) if helpful.\n"
        "Do not include tasks, exercises, assessments, or lesson plans.\n"
        "Do not label sections as 'Lesson', 'Day', or 'Task'.\n"
        "Resource guidance:\n"
        "- If you mention a resource, include a real, specific URL.\n"
        "- Prefer official docs and reputable tutorials.\n"
        "- Do not reference vague videos or placeholders.\n"
        "- If you cannot provide a concrete URL, omit the resource.\n\n"
        f"Node name: {name}\n"
        f"Labels: {labels}\n"
        f"Description: {description}\n"
        f"Learning style: {learning_style or 'not specified'}\n"
        f"Skill level: {skill_level}\n"
        f"Time available: {time_available}\n"
        f"Instruction: {instruction}\n"
        f"Lesson sequence: This is lesson {lesson_index} for this node.\n"
        f"{prior_section}"
    )

    model_used = (
        getattr(llm, "model_name", None)
        or getattr(llm, "model", None)
        or getattr(getattr(llm, "client", None), "model", None)
        or getattr(getattr(llm, "client", None), "model_name", None)
        or model
        or "unknown"
    )

    with trace(
        name="lesson_generation.generate_lesson",
        input={
            "workflow": "lesson_generation.generate_lesson",
            "model_used": model_used,
            "prompt": prompt,
            "node_id": node.get("id"),
            "node_name": name,
            "lesson_index": lesson_index,
        },
        tags=[
            "workflow:lesson_generation",
            "stage:generate_lesson",
            f"model:{model_used}",
            f"provider:{provider}",
            f"node_id:{node.get('id')}",
        ],
    ) as tr:
        try:
            response = await asyncio.wait_for(
                llm.ainvoke([("human", prompt)]),
                timeout=LESSON_TIMEOUT,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if tr is not None:
                tr.output = {"error": f"Lesson generation failed: {e}"}
            return {"error": f"Lesson generation failed: {e}"}

        content = str(response.content if hasattr(response, "content") else response)
        parsed = parse_lesson_content(content)

        if tr is not None:
            tr.output = {
                "raw": content,
                "parsed": parsed or {},
            }

        return parsed




async def generate_and_store_lesson(
    db,
    project_id: str,
    node: dict,
    profile: dict | None,
    lesson_index: int,
    prior_titles: list[str],
) -> dict:
    result = await generate_lesson(node, profile, lesson_index, prior_titles)
    if "error" in result:
        return result

    from uuid import uuid4

    lesson_id = f"lesson-{uuid4().hex[:8]}"
    title = _display_name(node)
    with span("db.save_project_lesson"):
        db.save_project_lesson(
            project_id,
            lesson_id,
            node.get("id"),
            title,
            result.get("explanation", ""),
            result.get("task", ""),
            lesson_index,
        )

    return {"lesson_id": lesson_id, **result}
