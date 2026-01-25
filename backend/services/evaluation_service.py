"""
Capstone Evaluation Service
Evaluates project submissions against a rubric and required skills.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any

from backend.config import config
from backend.llm.provider import get_llm
from backend.services.opik_client import log_metric, span, trace
from backend.services.prompt_registry import get_prompt_template, get_prompt_version


EVALUATION_TIMEOUT = config.llm.timeout_seconds
LOGGER = logging.getLogger("endstate.capstone_eval")

RUBRIC = {
    "criteria": [
        {
            "name": "Skill Application",
            "description": "Does the submission demonstrate correct application of each required skill?",
            "weight": 0.5,
        },
        {
            "name": "Conceptual Understanding",
            "description": "Does the explanation show understanding, not just surface usage?",
            "weight": 0.3,
        },
        {
            "name": "Completeness",
            "description": "Does the submission address the full project brief?",
            "weight": 0.2,
        },
    ],
    "passing_score": 0.7,
}


def _extract_json_block(content: str) -> dict | None:
    try:
        fence_match = re.search(r"```json\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
        if fence_match:
            return json.loads(fence_match.group(1))
        obj_match = re.search(r"(\{.*\})", content, flags=re.DOTALL)
        if obj_match:
            return json.loads(obj_match.group(1))
    except Exception:
        return None
    return None


async def _repair_json(llm, content: str) -> dict | None:
    prompt = (
        "Fix the JSON below. Return ONLY valid JSON with no extra text.\n\n"
        f"{content}"
    )
    try:
        response = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=min(30, EVALUATION_TIMEOUT))
    except Exception as exc:
        LOGGER.warning("[CapstoneEval] JSON repair failed: %s", exc)
        return None
    repaired = str(response.content if hasattr(response, "content") else response)
    return _extract_json_block(repaired)


def _normalize_skill(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _derive_required_skills(summary: dict, skill_nodes: list[str]) -> list[str]:
    skills = summary.get("skills") if isinstance(summary.get("skills"), list) else []
    cleaned = [skill.strip() for skill in skills if isinstance(skill, str) and skill.strip()]
    if cleaned:
        return list(dict.fromkeys(cleaned))
    return list(dict.fromkeys([s for s in skill_nodes if s]))


def _compute_skill_evidence(required: list[str], evidence: dict) -> dict:
    normalized = {_normalize_skill(k): v for k, v in evidence.items()} if isinstance(evidence, dict) else {}
    result = {}
    for skill in required:
        key = _normalize_skill(skill)
        value = normalized.get(key)
        if not value:
            result[skill] = "Missing - not addressed."
            continue
        result[skill] = str(value).strip()
    return result


def _skills_passed(skill_evidence: dict) -> bool:
    for value in skill_evidence.values():
        text = str(value).strip().lower()
        if not text or "missing" in text:
            return False
    return True


async def evaluate_submission(
    submission: str,
    project_brief: str,
    required_skills: list[str],
    model_used: str,
) -> dict[str, Any]:
    try:
        llm = get_llm()
    except Exception as exc:
        LOGGER.error("[CapstoneEval] LLM init failed: %s", exc)
        return {"error": f"Evaluation failed: {exc}"}

    def _escape_braces(value: str) -> str:
        return value.replace("{", "{{").replace("}", "}}")

    skill_list = "\n".join(f"- {skill}" for skill in required_skills) if required_skills else "- None provided"
    rubric_text = json.dumps(RUBRIC, indent=2)

    prompt_name = os.getenv("ENDSTATE_CAPSTONE_PROMPT", "capstone_evaluation").strip()
    template = get_prompt_template(prompt_name)
    prompt_version = get_prompt_version(prompt_name)

    prompt = template.format(
        project_brief=_escape_braces(project_brief),
        skills=_escape_braces(skill_list),
        submission=_escape_braces(submission),
        rubric=_escape_braces(rubric_text),
    )
    opik_input = {
        "prompt_name": prompt_name,
        "prompt_version": prompt_version,
        "model_used": model_used,
        "required_skills": required_skills,
        "required_skills_count": len(required_skills),
        "prompt_chars": len(prompt),
        "submission_len": len(submission),
        "project_brief_len": len(project_brief),
    }



    debug_enabled = os.getenv("ENDSTATE_EVAL_DEBUG", "").lower() in {"1", "true", "yes"}
    LOGGER.warning(
        "[CapstoneEval] start provider=%s prompt_chars=%s skills=%s",
        model_used,
        len(prompt),
        len(required_skills),
    )

    with trace(
        name="capstone_evaluation",
        input=opik_input,
        tags=["endstate", "capstone", prompt_name, prompt_version],
    ) as t:
        with span("prompt_generation", metadata={"prompt_chars": len(prompt)}):
            pass

        llm_t0 = time.time()
        try:
            with span("llm_call", metadata={"model_used": model_used, "prompt_name": prompt_name, "prompt_version": prompt_version}):
                response = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=EVALUATION_TIMEOUT)
        except Exception as e:
            LOGGER.warning("[CapstoneEval] error=%s", e)
            if t is not None:
                t.output = {"error": str(e)}
                t.metadata = {"latency_ms": int((time.time() - llm_t0) * 1000)}
            return {"error": f"Evaluation failed: {e}"}

        llm_latency_ms = int((time.time() - llm_t0) * 1000)

        content = str(response.content if hasattr(response, "content") else response)

        with span("parsing"):
            parsed = _extract_json_block(content)
            parse_error = None
            if not parsed:
                repaired = await _repair_json(llm, content)
                if repaired:
                    parsed = repaired
                else:
                    parse_error = "Evaluation response was not valid JSON."
                    parsed = {}

        with span("scoring"):
            raw_score = parsed.get("score")
            score = 0.0
            if raw_score is not None:
                try:
                    score = float(raw_score)
                except (TypeError, ValueError):
                    if isinstance(raw_score, str):
                        match = re.search(r"-?\d+(?:\.\d+)?", raw_score)
                        if match:
                            try:
                                score = float(match.group(0))
                            except ValueError:
                                score = 0.0
                    if score == 0.0:
                        parse_error = parse_error or "Evaluation score was not a number."

            criteria = parsed.get("criteria") if isinstance(parsed.get("criteria"), dict) else {}
            skill_evidence = _compute_skill_evidence(required_skills, parsed.get("skill_evidence") or {})
            passed = score >= RUBRIC["passing_score"] and _skills_passed(skill_evidence)

            overall_feedback = str(parsed.get("overall_feedback") or "").strip()
            if parse_error and not overall_feedback:
                overall_feedback = "Evaluation failed to parse. Please resubmit."

            suggestions = parsed.get("suggestions") if isinstance(parsed.get("suggestions"), list) else []

        snippet = content[:500].replace("\n", " ")
        if debug_enabled:
            LOGGER.info("[CapstoneEval] response_snippet=%s", snippet)
        if parse_error:
            LOGGER.warning("[CapstoneEval] parse_error=%s snippet=%s", parse_error, snippet)

        log_metric("capstone.score", float(score))
        log_metric("capstone.passed", 1.0 if passed else 0.0)
        log_metric("capstone.llm_latency_ms", float(llm_latency_ms))

        if t is not None:
            t.output = {
                "score": score,
                "passed": passed,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
            }
            t.metadata = {
                "latency_ms": llm_latency_ms,
                "parse_error": parse_error,
            }


        return {
            "score": score,
            "criteria": criteria,
            "skill_evidence": skill_evidence,
            "overall_feedback": overall_feedback,
            "suggestions": suggestions,
            "passed": passed,
            "model_used": model_used,
            "prompt_version": prompt_version,
            "parse_error": parse_error,
            "latency_ms": llm_latency_ms,
        }



def build_project_brief(summary: dict) -> str:
    agreed = summary.get("agreed_project", {}) if isinstance(summary.get("agreed_project"), dict) else {}
    parts = [
        f"Project: {agreed.get('name', '')}",
        f"Description: {agreed.get('description', '')}",
        f"Timeline: {agreed.get('timeline', '')}",
    ]
    milestones = agreed.get("milestones") if isinstance(agreed.get("milestones"), list) else []
    if milestones:
        parts.append("Milestones: " + "; ".join(milestones))
    return "\n".join([part for part in parts if part.strip()])


def derive_required_skills(summary: dict, skill_nodes: list[str]) -> list[str]:
    return _derive_required_skills(summary, skill_nodes)


async def evaluate_project_alignment(goal: str, project: dict) -> dict[str, Any]:
    """Evaluate alignment between user goal and project brief."""
    llm = get_llm()
    project_name = project.get("name", "")
    project_desc = project.get("description", "")
    template = get_prompt_template("project_alignment")
    prompt = template.format(goal=goal, project_name=project_name, project_description=project_desc)
    try:
        response = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=EVALUATION_TIMEOUT)
    except Exception as e:
        return {"error": f"Alignment evaluation failed: {e}"}
    content = str(response.content if hasattr(response, "content") else response)
    parsed = _extract_json_block(content) or {}
    score = float(parsed.get("score") or 0.0)
    return {
        "score": score,
        "critique": str(parsed.get("critique") or "").strip(),
        "prompt_version": get_prompt_version("project_alignment"),
    }


async def evaluate_kg_quality(project: dict, summary: dict) -> dict[str, Any]:
    """Evaluate KG quality based on project brief + extracted skills/topics."""
    llm = get_llm()
    skills = summary.get("skills", []) if isinstance(summary.get("skills"), list) else []
    topics = summary.get("topics", []) if isinstance(summary.get("topics"), list) else []
    concepts = summary.get("concepts", []) if isinstance(summary.get("concepts"), list) else []
    template = get_prompt_template("kg_quality")
    prompt = template.format(
        project_name=project.get("name", ""),
        project_description=project.get("description", ""),
        skills=", ".join(skills),
        topics=", ".join(topics),
        concepts=", ".join(concepts),
    )
    try:
        response = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=EVALUATION_TIMEOUT)
    except Exception as e:
        return {"error": f"KG evaluation failed: {e}"}
    content = str(response.content if hasattr(response, "content") else response)
    parsed = _extract_json_block(content) or {}
    return {
        "coverage_score": float(parsed.get("coverage_score") or 0.0),
        "redundancy_score": float(parsed.get("redundancy_score") or 0.0),
        "critique": str(parsed.get("critique") or "").strip(),
        "prompt_version": get_prompt_version("kg_quality"),
    }
