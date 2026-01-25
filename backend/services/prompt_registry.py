"""
Prompt registry for tracking prompt versions.
"""
from __future__ import annotations

from typing import Dict


PROMPTS: Dict[str, dict] = {
    "capstone_evaluation": {
        "version": "capstone_eval_v1",
        "template": (
            "You are an expert educator evaluating a capstone submission.\n"
            "Return ONLY valid JSON.\n\n"
            "PROJECT BRIEF:\n{project_brief}\n\n"
            "REQUIRED SKILLS:\n{skills}\n\n"
            "SUBMISSION:\n{submission}\n\n"
            "Evaluate using this rubric:\n{rubric}\n\n"
            "Output JSON with keys:\n"
            "{{\n"
            '  "score": 0.0-1.0,\n'
            '  "criteria": {{\n'
            '    "skill_application": {{"score": 0.0-1.0, "strengths": [], "weaknesses": [], "suggestions": []}},\n'
            '    "conceptual_understanding": {{"score": 0.0-1.0, "strengths": [], "weaknesses": [], "suggestions": []}},\n'
            '    "completeness": {{"score": 0.0-1.0, "strengths": [], "weaknesses": [], "suggestions": []}}\n'
            "  }},\n"
            '  "skill_evidence": {{"Skill Name": "Where/how demonstrated OR Missing - reason"}},\n'
            '  "overall_feedback": "Encouraging, specific improvement guidance",\n'
            '  "suggestions": ["Specific improvement suggestions"]\n'
            "}}\n"
        ),
    },
    "project_alignment": {
        "version": "project_alignment_v1",
        "template": (
            "Evaluate alignment between the user goal and the proposed project.\n"
            "Return JSON with keys: score (0-1), critique.\n\n"
            "User goal: {goal}\n"
            "Project name: {project_name}\n"
            "Project description: {project_description}\n"
        ),
    },
    "capstone_evaluation_v2": {
        "version": "capstone_eval_v2",
        "template": (
            "You are a strict capstone evaluator.\n"
            "Return ONLY valid JSON. No markdown. No explanations.\n"
            "Evaluate strictly based on the submission text.\n"
            "If something is not explicitly stated, it does NOT exist.\n\n"

            "PROJECT BRIEF:\n{project_brief}\n\n"
            "REQUIRED SKILLS:\n{skills}\n\n"
            "SUBMISSION:\n{submission}\n\n"

            "EVALUATION RULES:\n"
            "- Every claimed skill must be supported by a direct quote from the submission.\n"
            "- If a skill is not clearly supported, mark it as \"Missing - not evidenced in submission\".\n"
            "- Penalize vague claims such as \"optimized\", \"robust\", \"state-of-the-art\", or \"worked perfectly\".\n"
            "- Missing implementation details must reduce the score.\n"
            "- If 2 or more skills are missing, overall score must be <= 0.49.\n"
            "- Criteria scores must logically align with the overall score.\n\n"

            "Return a JSON object with exactly these keys:\n"
            "score, criteria, skill_evidence, overall_feedback, suggestions\n\n"

            "{{\n"
            "  \"score\": 0.0,\n"
            "  \"criteria\": {{\n"
            "    \"skill_application\": {{\"score\": 0.0, \"strengths\": [], \"weaknesses\": [], \"suggestions\": []}},\n"
            "    \"conceptual_understanding\": {{\"score\": 0.0, \"strengths\": [], \"weaknesses\": [], \"suggestions\": []}},\n"
            "    \"completeness\": {{\"score\": 0.0, \"strengths\": [], \"weaknesses\": [], \"suggestions\": []}}\n"
            "  }},\n"
            "  \"skill_evidence\": {{\n"
            "    \"Skill Name\": \"Direct quote from submission, or Missing - not evidenced in submission\"\n"
            "  }},\n"
            "  \"overall_feedback\": \"\",\n"
            "  \"suggestions\": []\n"
            "}}\n"
        ),
    },


    "kg_quality": {
        "version": "kg_quality_v1",
        "template": (
            "Evaluate the quality of extracted skills/topics for the project.\n"
            "Return JSON with keys: coverage_score (0-1), redundancy_score (0-1), critique.\n\n"
            "Project name: {project_name}\n"
            "Project description: {project_description}\n"
            "Skills: {skills}\n"
            "Topics: {topics}\n"
            "Concepts: {concepts}\n"
        ),
    },
}


def get_prompt_version(name: str) -> str:
    entry = PROMPTS.get(name, {})
    return entry.get("version", "unknown")


def get_prompt_template(name: str) -> str:
    entry = PROMPTS.get(name, {})
    return entry.get("template", "")
