"""
Remediation Service
Diagnose assessment failures and generate remediation nodes for the knowledge graph.

This service implements self-healing behavior for the learning system:
1. Analyzes why a learner failed an assessment
2. Identifies missing or weak prerequisite concepts
3. Generates remediation nodes to insert into the graph
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

from backend.config import config
from backend.llm.provider import get_llm

logger = logging.getLogger(__name__)

REMEDIATION_TIMEOUT = config.llm.timeout_seconds


def _extract_json_block(content: str) -> dict | None:
    """Extract JSON from LLM response."""
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


async def diagnose_failure(
    lesson: dict,
    assessment: dict,
    answer: str,
    feedback: str,
    node_context: Optional[dict] = None,
) -> dict:
    """
    Diagnose why a learner failed an assessment.
    
    Args:
        lesson: The lesson dict containing explanation
        assessment: The assessment dict containing prompt
        answer: The learner's incorrect answer
        feedback: The evaluation feedback explaining why it failed
        node_context: Optional context about the node's prerequisites
        
    Returns:
        Dictionary with:
            - diagnosis: Semantic description of the failure
            - missing_concepts: List of prerequisite concepts to reinforce
            - severity: "minor", "moderate", or "major"
            - recommended_action: "hint", "review_prerequisite", or "insert_prerequisite"
    """
    llm = get_llm()
    
    lesson_title = lesson.get("title", "Unknown topic")
    lesson_explanation = lesson.get("explanation", "")[:500]
    assessment_prompt = assessment.get("prompt", "")
    
    prereq_context = ""
    if node_context and node_context.get("prerequisites"):
        prereqs = ", ".join(node_context.get("prerequisites", []))
        prereq_context = f"\nKnown prerequisites for this topic: {prereqs}"
    
    prompt = (
        "You are a learning diagnostician. Analyze why a learner failed this assessment.\n"
        "Return JSON with keys: diagnosis, missing_concepts, severity, recommended_action.\n\n"
        "Requirements:\n"
        "- diagnosis: 1-2 sentence semantic description of the conceptual gap\n"
        "- missing_concepts: list of 1-3 prerequisite concept names (short titles)\n"
        "- severity: 'minor' (small gap), 'moderate' (needs prerequisite), 'major' (fundamental gap)\n"
        "- recommended_action: 'hint' | 'review_prerequisite' | 'insert_prerequisite'\n\n"
        f"Topic: {lesson_title}\n"
        f"Lesson content (excerpt): {lesson_explanation}\n"
        f"Assessment prompt: {assessment_prompt}\n"
        f"Learner's answer: {answer}\n"
        f"Evaluation feedback: {feedback}\n"
        f"{prereq_context}"
    )
    
    try:
        response = await asyncio.wait_for(
            llm.ainvoke([("human", prompt)]),
            timeout=REMEDIATION_TIMEOUT
        )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Diagnosis failed: {e}")
        return {
            "error": f"Diagnosis failed: {e}",
            "diagnosis": "Unable to diagnose failure",
            "missing_concepts": [],
            "severity": "moderate",
            "recommended_action": "review_prerequisite",
        }
    
    content = str(response.content if hasattr(response, "content") else response)
    parsed = _extract_json_block(content)
    
    if not parsed:
        return {
            "diagnosis": content.strip()[:200],
            "missing_concepts": [],
            "severity": "moderate",
            "recommended_action": "review_prerequisite",
        }
    
    return {
        "diagnosis": str(parsed.get("diagnosis", "")).strip(),
        "missing_concepts": parsed.get("missing_concepts", []),
        "severity": str(parsed.get("severity", "moderate")).lower(),
        "recommended_action": str(parsed.get("recommended_action", "review_prerequisite")),
    }


async def generate_remediation_content(
    diagnosis: dict,
    original_node: dict,
    profile: Optional[dict] = None,
) -> dict:
    """
    Generate content for a remediation node based on diagnosis.
    
    Args:
        diagnosis: Result from diagnose_failure()
        original_node: The node the learner was struggling with
        profile: Optional learner profile for personalization
        
    Returns:
        Dictionary with remediation node properties:
            - title: Short title for the remediation concept
            - description: Description of what this remediation covers
            - explanation: Focused lesson content
    """
    llm = get_llm()
    
    missing_concepts = diagnosis.get("missing_concepts", [])
    if not missing_concepts:
        missing_concepts = ["foundational understanding"]
    
    primary_concept = missing_concepts[0] if missing_concepts else "prerequisite concept"
    original_name = original_node.get("properties", {}).get("name") or original_node.get("name", "the topic")
    diagnosis_text = diagnosis.get("diagnosis", "conceptual gap identified")
    
    learning_style = (profile or {}).get("learning_style", "")
    skill_level = (profile or {}).get("skill_level", "intermediate")
    
    prompt = (
        "Create a focused remediation lesson for a learner who struggled with a concept.\n"
        "Return JSON with keys: title, description, explanation.\n\n"
        "Requirements:\n"
        "- title: Short title (2-5 words) for this remediation topic\n"
        "- description: 1-2 sentence description of what this covers\n"
        "- explanation: 3-5 paragraph focused explanation covering the gap\n\n"
        f"Original topic the learner struggled with: {original_name}\n"
        f"Diagnosed gap: {diagnosis_text}\n"
        f"Missing concept to address: {primary_concept}\n"
        f"Skill level: {skill_level}\n"
        f"Learning style: {learning_style or 'balanced'}\n"
    )
    
    try:
        response = await asyncio.wait_for(
            llm.ainvoke([("human", prompt)]),
            timeout=REMEDIATION_TIMEOUT
        )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Remediation content generation failed: {e}")
        return {
            "error": f"Content generation failed: {e}",
            "title": f"Review: {primary_concept}",
            "description": f"Reinforcement of {primary_concept} before continuing.",
            "explanation": f"Please review the fundamentals of {primary_concept}.",
        }
    
    content = str(response.content if hasattr(response, "content") else response)
    parsed = _extract_json_block(content)
    
    if not parsed:
        return {
            "title": f"Review: {primary_concept}",
            "description": f"Reinforcement of {primary_concept}.",
            "explanation": content.strip()[:1000],
        }
    
    return {
        "title": str(parsed.get("title", parsed.get("name", f"Review: {primary_concept}"))).strip(),
        "description": str(parsed.get("description", "")).strip(),
        "explanation": str(parsed.get("explanation", "")).strip(),
    }


def create_remediation_node(
    db,
    project_id: str,
    node_id: str,
    remediation_content: dict,
    diagnosis: dict,
    before_node_id: str,
    assessment_id: str,
) -> dict:
    """
    Create a remediation node in the graph and insert it before the target node.
    
    Args:
        db: Neo4jClient instance
        project_id: Project this remediation belongs to
        node_id: Generated node ID
        remediation_content: Content from generate_remediation_content()
        diagnosis: Original diagnosis from diagnose_failure()
        before_node_id: The node to insert this remediation before
        assessment_id: The assessment that triggered this remediation
        
    Returns:
        Dictionary with created node info
    """
    result = db.create_remediation_node(
        project_id=project_id,
        node_id=node_id,
        title=remediation_content.get("title", remediation_content.get("name", "Remediation")),
        description=remediation_content.get("description", ""),
        explanation=remediation_content.get("explanation", ""),
        diagnosis=diagnosis.get("diagnosis", ""),
        severity=diagnosis.get("severity", "moderate"),
        before_node_id=before_node_id,
        triggered_by_assessment=assessment_id,
    )
    
    return result


async def remediate_assessment_failure(
    db,
    project_id: str,
    assessment_id: str,
    lesson: dict,
    assessment: dict,
    answer: str,
    feedback: str,
    node_id: str,
    profile: Optional[dict] = None,
) -> dict:
    """
    Full remediation pipeline: diagnose, generate content, create node.
    
    Args:
        db: Neo4jClient instance
        project_id: Project ID
        assessment_id: Assessment that was failed
        lesson: Lesson dict
        assessment: Assessment dict  
        answer: Learner's failing answer
        feedback: Evaluation feedback
        node_id: The KG node this assessment was for
        profile: Optional learner profile
        
    Returns:
        Dictionary with remediation results
    """
    from uuid import uuid4
    
    # Get node context for better diagnosis
    node_result = db.get_node_by_id(node_id)
    original_node = {}
    if node_result:
        from backend.db.neo4j_client import _serialize_node
        original_node = _serialize_node(node_result.get("node"))
    
    # Get prerequisites for context
    prereqs = db.get_prerequisite_nodes(node_id)
    node_context = {"prerequisites": [p.get("name") for p in prereqs]}
    
    # Step 1: Diagnose
    diagnosis = await diagnose_failure(
        lesson=lesson,
        assessment=assessment,
        answer=answer,
        feedback=feedback,
        node_context=node_context,
    )
    
    if diagnosis.get("error"):
        logger.warning(f"Diagnosis failed: {diagnosis.get('error')}")
    
    # Check if remediation warranted
    if diagnosis.get("recommended_action") == "hint":
        return {
            "action": "hint",
            "diagnosis": diagnosis,
            "remediation_created": False,
            "message": "Minor gap - hint recommended instead of new node",
        }
    
    # Step 2: Generate remediation content
    remediation_content = await generate_remediation_content(
        diagnosis=diagnosis,
        original_node=original_node,
        profile=profile,
    )
    
    if remediation_content.get("error"):
        logger.warning(f"Content generation failed: {remediation_content.get('error')}")
    
    # Step 3: Create the remediation node
    remediation_node_id = f"remediation-{uuid4().hex[:8]}"
    
    node_result = create_remediation_node(
        db=db,
        project_id=project_id,
        node_id=remediation_node_id,
        remediation_content=remediation_content,
        diagnosis=diagnosis,
        before_node_id=node_id,
        assessment_id=assessment_id,
    )
    
    # Track the event
    db.track_remediation_event(
        project_id=project_id,
        assessment_id=assessment_id,
        remediation_node_id=remediation_node_id,
        diagnosis_summary=diagnosis.get("diagnosis", ""),
        severity=diagnosis.get("severity", "moderate"),
    )
    
    return {
        "action": "node_created",
        "diagnosis": diagnosis,
        "remediation_node_id": remediation_node_id,
        "remediation_content": remediation_content,
        "remediation_created": True,
        "before_node_id": node_id,
        "message": f"Created remediation node: {remediation_content.get('name')}",
    }
