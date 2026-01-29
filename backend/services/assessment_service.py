"""
Assessment Service
Generate and evaluate assessments for lessons.
"""
from __future__ import annotations

import asyncio

import json
import os
from backend.config import config
from backend.llm.provider import get_llm
from backend.services.opik_client import trace, span

from .utils import extract_json, clean_markdown



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


# Removed _extract_json_block in favor of .utils.extract_json


def parse_assessment_content(content: str) -> dict:
    data = extract_json(content)
    if data:
        # Flexible mapping for common synonym keys
        if "prompt" not in data:
            for key in ["question", "problem", "task", "assessment"]:
                if key in data:
                    data["prompt"] = data[key]
                    break
        
        if "result" not in data:
            for key in ["score", "status", "outcome"]:
                if key in data:
                    data["result"] = data[key]
                    break

        return data
        
    cleaned = clean_markdown(content)
    return {"raw": cleaned}


async def generate_assessment(lesson: dict, profile: dict | None) -> dict:
    llm = get_llm()

    explanation = lesson.get("explanation", "").strip()
    if not explanation:
        return {"error": "Cannot generate assessment for lesson with no content."}

    learning_style = (profile or {}).get("learning_style", "")
    prompt = (
        "Create one assessment prompt based on the lesson below.\n"
        "Return JSON with key: prompt.\n"
        "Use only the lesson content; do not invent new scope.\n\n"
        f"Lesson explanation: {lesson.get('explanation', '')}\n"
        f"Learning style: {learning_style or 'not specified'}\n"
        f"Instruction: {_style_hint(learning_style)}\n"
    )

    model = (os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL") or "").strip()
    provider = (os.getenv("LLM_PROVIDER") or "openrouter").strip()

    if not model:
        model = (
            getattr(getattr(config, "llm", None), "model", None)
            or getattr(getattr(config, "llm", None), "model_name", None)
            or "unknown"
        )


    trace_input = {
        "workflow": "assessment_generation",
        "learning_style": learning_style or "not specified",
        "lesson": lesson,
        "model": model,
        "provider": provider,
        "prompt": prompt,
    }

    with trace(
        "endstate.assessment.generate",
        input=trace_input,
        tags=[
            "workflow:assessment",
            "step:generate",
            f"model:{model}",
            f"provider:{provider}",
        ],
    ) as t:
        try:
            with span("llm.call"):
                response = await asyncio.wait_for(
                    llm.ainvoke([("human", prompt)]),
                    timeout=ASSESSMENT_TIMEOUT,
                )
        except Exception as e:
            if t is not None:
                t.output = {"error": f"Assessment generation failed: {e}"}
            return {"error": f"Assessment generation failed: {e}"}

        content = str(response.content if hasattr(response, "content") else response)
        parsed = parse_assessment_content(content)

        if "prompt" in parsed:
            out = {"prompt": str(parsed.get("prompt", "")).strip()}
        else:
            out = {"prompt": str(parsed.get("raw", "")).strip()}

        if t is not None:
            t.output = {
                "parsed": parsed,
                "output": out,
            }

        return out



async def evaluate_assessment(lesson: dict, assessment: dict, answer: str) -> dict:
    llm = get_llm()

    prompt = (
        "Evaluate the learner's answer. Return JSON with keys: result (pass|fail), feedback.\n\n"
        f"Lesson explanation: {lesson.get('explanation', '')}\n"
        f"Assessment prompt: {assessment.get('prompt', '')}\n"
        f"Learner answer: {answer}\n"
    )

    model = (os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL") or "").strip()
    provider = (os.getenv("LLM_PROVIDER") or "openrouter").strip()

    if not model:
        model = (
            getattr(getattr(config, "llm", None), "model", None)
            or getattr(getattr(config, "llm", None), "model_name", None)
            or "unknown"
        )
    trace_input = {
        "workflow": "assessment_evaluation",
        "lesson": lesson,
        "assessment": assessment,
        "answer": answer,
        "model": model,
        "provider": provider,
        "prompt": prompt,
    }

    with trace(
        "endstate.assessment.evaluate",
        input=trace_input,
        tags=[
            "workflow:assessment",
            "step:evaluate",
            f"model:{model}",
            f"provider:{provider}",
        ],
    ) as t:
        try:
            with span("llm.call"):
                response = await asyncio.wait_for(
                    llm.ainvoke([("human", prompt)]),
                    timeout=ASSESSMENT_TIMEOUT,
                )
        except Exception as e:
            if t is not None:
                t.output = {"error": f"Assessment evaluation failed: {e}"}
            return {"error": f"Assessment evaluation failed: {e}"}

        content = str(response.content if hasattr(response, "content") else response)
        parsed = parse_assessment_content(content)

        if "result" in parsed:
            result = str(parsed.get("result", "")).strip().lower()
            if result not in {"pass", "fail"}:
                result = "fail"
            out = {"result": result, "feedback": str(parsed.get("feedback", "")).strip()}
        else:
            out = {"result": "fail", "feedback": str(parsed.get("raw", "")).strip()}

        if t is not None:
            t.output = {
                "parsed": parsed,
                "output": out,
            }

        return out

