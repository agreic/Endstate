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
from backend.services.opik_client import trace, span, log_metric

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
        raw_prereqs = node_context.get("prerequisites", [])
        # Ensure we only try to join strings
        prereq_list = [str(p) for p in raw_prereqs if p is not None]
        if prereq_list:
            prereqs = ", ".join(prereq_list)
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
    
    model_used = (
        getattr(llm, "model_name", None)
        or getattr(llm, "model", None)
        or getattr(getattr(llm, "client", None), "model", None)
        or getattr(getattr(llm, "client", None), "model_name", None)
        or "unknown"
    )


    with trace(
        name="assessment_evaluation.diagnose_failure",
        input={
            "workflow": "assessment_evaluation.diagnose_failure",
            "model_used": model_used,
            "prompt": prompt,
        },
        tags=["workflow:assessment_evaluation", "stage:diagnose_failure"],
    ) as tr:
        try:
            response = await asyncio.wait_for(
                llm.ainvoke([("human", prompt)]),
                timeout=REMEDIATION_TIMEOUT
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Diagnosis failed: {e}")
            if tr is not None:
                tr.output = {"error": str(e)}
            return {
                "error": f"Diagnosis failed: {e}",
                "diagnosis": "Unable to diagnose failure",
                "missing_concepts": [],
                "severity": "moderate",
                "recommended_action": "review_prerequisite",
            }

        content = str(response.content if hasattr(response, "content") else response)
        parsed = _extract_json_block(content)

        if tr is not None:
            tr.output = {
                "raw": content,
                "parsed": parsed or {},
            }

    if not parsed:
        return {
            "diagnosis": content.strip()[:200],
            "missing_concepts": [],
            "severity": "moderate",
            "recommended_action": "review_prerequisite",
            "_opik": {
                "prompt": prompt,
                "raw": content,
                "parsed": {},
                "model_used": model_used,
            },
        }

    return {
        "diagnosis": str(parsed.get("diagnosis", "")).strip(),
        "missing_concepts": parsed.get("missing_concepts", []),
        "severity": str(parsed.get("severity", "moderate")).lower(),
        "recommended_action": str(parsed.get("recommended_action", "review_prerequisite")),
        "_opik": {
            "prompt": prompt,
            "raw": content,
            "parsed": parsed or {},
            "model_used": model_used,
        },
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
    
    prompt = f"""You are the Senior Remediation Specialist.

YOUR TASK:
Create a "Bridge Lesson" that fills a specific knowledge gap identified in a student's recent failure.
You must explain the missing concept in a way that connects it back to the original topic.

INPUT CONTEXT:
- **Failed Topic:** {original_name}
- **Diagnosed Gap:** {diagnosis_text}
- **Missing Concept:** {primary_concept}
- **Student Profile:** {skill_level} / {learning_style or 'balanced'}

DESIGN PHILOSOPHY:
1. **The "Bridge" Approach:** Do not just repeat the original lesson. Explain the *missing ingredient* (the concept) and how it makes the original topic work.
2. **Analogy First:** Start with a non-technical analogy if the learning style permits.
3. **Concrete Examples:** If the gap is technical, provide a minimal, correct code snippet demonstrating ONLY that concept.

OUTPUT FORMAT:
Return strictly valid JSON. Do not include markdown formatting (```json).

JSON SCHEMA:
{{
  "remediation": {{
      "title": "Title (e.g., 'Understanding the Base Case')",
      "description": "1 sentence on why this specific concept matters.",
      "explanation": "A rich, detailed explanation (approx. 200 words). Use line breaks (\\n) for readability. Include an analogy and a technical example.",
      "bridge_connection": "One sentence explaining how this concept fixes their error in '{original_name}'."
  }}
}}
"""
    raw_content = ""

    parsed_top = None  
    try:
        model_used = (
            getattr(llm, "model_name", None)
            or getattr(llm, "model", None)
            or getattr(getattr(llm, "client", None), "model", None)
            or getattr(getattr(llm, "client", None), "model_name", None)
            or "unknown"
        )

        with trace(
            name="assessment_evaluation.generate_remediation",
            input={
                "workflow": "assessment_evaluation.generate_remediation",
                "model_used": model_used,
                "prompt": prompt,
            },
            tags=["workflow:assessment_evaluation", "stage:generate_remediation"],
        ) as tr:

            response = await asyncio.wait_for(
                llm.ainvoke([("human", prompt)]),
                timeout=REMEDIATION_TIMEOUT
            )

            content = str(response.content if hasattr(response, "content") else response)
            parsed_top = _extract_json_block(content)

            if tr is not None:
                tr.output = {
                    "raw": content,
                    "parsed": parsed_top or {},
                }


        parsed = parsed_top
        # Handle nested "remediation" key from new schema
        if parsed and "remediation" in parsed:
            parsed = parsed["remediation"]
        
        if parsed:
            explanation = str(parsed.get("explanation", "")).strip()
            bridge = str(parsed.get("bridge_connection", "")).strip()
            
            # Append bridge connection to explanation if present
            if bridge and bridge not in explanation:
                explanation = f"{explanation}\n\n**Connection:** {bridge}"
            
            # Check for minimum length to avoid "empty" lessons
            if explanation and len(explanation) >= 100:
                return {
                    "title": str(parsed.get("title", parsed.get("name", f"Review: {primary_concept}"))).strip(),
                    "description": str(parsed.get("description", "")).strip(),
                    "explanation": explanation,
                    "_opik": {
                        "prompt": prompt,
                        "raw": raw_content,
                        "parsed": parsed_top or {},
                        },
                }
        
        # Content was too short or failed to parse
        logger.warning(f"Remediation generation produced insufficient content. Raw: {content[:200]}")
        return {
            "error": "LLM produced insufficient remediation content.",
            "title": f"Review: {primary_concept}",
            "description": f"Reinforcement of {primary_concept}.",
            "explanation": f"Unable to generate detailed lesson. Please review the fundamentals of {primary_concept}.",
            "_opik": {
                "prompt": prompt,
                "raw": raw_content,
                "parsed": parsed_top or {},
            },
        }
        
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Remediation content generation failed: {e}")
        return {
            "error": f"LLM failed: {e}",
            "title": f"Review: {primary_concept}",
            "description": f"Reinforcement of {primary_concept}.",
            "explanation": f"Unable to generate detailed lesson. Please review the fundamentals of {primary_concept}.",
            "_opik": {
                "prompt": prompt,
                "raw": raw_content,
                "parsed": parsed_top or {},
            },
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
    trace_input = {
        "workflow": "remediation",
        "project_id": project_id,
        "assessment_id": assessment_id,
        "node_id": node_id,
        "has_profile": bool(profile),
        "answer_chars": len(answer or ""),
        "feedback_chars": len(feedback or ""),
    }

    tags = [
        "workflow:remediation",
        f"project_id:{project_id}",
        f"assessment_id:{assessment_id}",
    ]
    diagnosis: dict = {}
    remediation_content: dict = {}

    with trace("endstate.remediation.run", input=trace_input, tags=tags) as t:

        # Get node context for better diagnosis
        node_result = db.get_node_by_id(node_id)
        original_node = {}
        if node_result:
            from backend.db.neo4j_client import _serialize_node
            original_node = _serialize_node(node_result.get("node"))

        # Get prerequisites for context
        prereqs = db.get_prerequisite_nodes(node_id)
        node_context = {"prerequisites": [p.get("name") for p in prereqs if p.get("name")]}

        # Step 1: Diagnose
        with span("llm.diagnose_failure"):
            diagnosis = await diagnose_failure(
                lesson=lesson,
                assessment=assessment,
                answer=answer,
                feedback=feedback,
                node_context=node_context,
            )

        if diagnosis.get("error"):
            logger.warning(f"Diagnosis failed: {diagnosis.get('error')}")
            return {
                "action": "failed",
                "error": diagnosis.get("error"),
                "message": "Failed to diagnose assessment failure.",
                "remediation_created": False,
            }

        # Check if remediation warranted
        if diagnosis.get("recommended_action") == "hint":
            return {
                "action": "hint",
                "diagnosis": diagnosis,
                "remediation_created": False,
                "message": "Minor gap - hint recommended instead of new node",
            }

        # Step 2: Generate remediation content
        with span("llm.generate_remediation"):
            remediation_content = await generate_remediation_content(
                diagnosis=diagnosis,
                original_node=original_node,
                profile=profile,
            )

        if remediation_content.get("error"):
            logger.warning(f"Content generation failed: {remediation_content.get('error')}")
            return {
                "action": "failed",
                "error": remediation_content.get("error"),
                "message": "Failed to generate remediation content.",
                "remediation_created": False,
            }

        # Step 3: Create the remediation node
        remediation_node_id = f"remediation-{uuid4().hex[:8]}"

        with span("db.create_remediation_node"):
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

        log_metric(
            "remediation.node_created",
            1.0,
            session_id=project_id,
            tags=tags,
        )

        if t is not None:
            t.output = {
                "status": "ok",
                "project_id": project_id,
                "assessment_id": assessment_id,
                "node_id": node_id,
                "remediation_node_id": remediation_node_id,
                "diagnosis": {
                    "diagnosis": diagnosis.get("diagnosis"),
                    "missing_concepts": diagnosis.get("missing_concepts", []),
                    "severity": diagnosis.get("severity"),
                    "recommended_action": diagnosis.get("recommended_action"),
                },
                "remediation": {
                    "title": remediation_content.get("title"),
                    "description": remediation_content.get("description"),
                    "explanation_chars": len((remediation_content.get("explanation") or "")),
                },
                "llm": {
                    "diagnose_failure": {
                        "raw": (diagnosis.get("_opik") or {}).get("raw", ""),
                        "parsed": (diagnosis.get("_opik") or {}).get("parsed", {}),
                    },
                    "generate_remediation": {
                        "raw": (remediation_content.get("_opik") or {}).get("raw", ""),
                        "parsed": (remediation_content.get("_opik") or {}).get("parsed", {}),
                    },
                },

            }


        return {
            "action": "node_created",
            "diagnosis": diagnosis,
            "remediation_node_id": remediation_node_id,
            "remediation_content": remediation_content,
            "remediation_created": True,
            "before_node_id": node_id,
            "message": f"Created remediation node: {remediation_content.get('title')}",
        }

