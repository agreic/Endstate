#!/usr/bin/env python3
"""
Create or cleanup a test project with skills via the Endstate API.

Usage:
  python scripts/test_project_cycle.py create
  python scripts/test_project_cycle.py cleanup
  python scripts/test_project_cycle.py create --project-id project-test-script --skills "Python,Lambdas"
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.parse
import urllib.request


def _encode_params(payload: dict) -> str:
    raw = json.dumps(payload).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _call_query(base_url: str, cypher: str, params: dict) -> dict:
    query = urllib.parse.urlencode({
        "cypher": cypher,
        "params": _encode_params(params),
    })
    url = f"{base_url.rstrip('/')}/api/query?{query}"
    with urllib.request.urlopen(url) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def _slugify(value: str) -> str:
    safe = []
    for ch in value.lower().strip():
        if ch.isalnum():
            safe.append(ch)
        elif ch in {" ", "-", "_"}:
            safe.append("-")
    slug = "".join(safe).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "skill"


def _create(base_url: str, project_id: str, project_name: str, skills: list[str]) -> None:
    summary = {
        "project_id": project_id,
        "session_id": project_id,
        "agreed_project": {
            "name": project_name,
            "description": "Seeded by test_project_cycle.py",
            "timeline": "",
            "milestones": [],
        },
        "user_profile": {
            "interests": ["test"],
            "skill_level": "intermediate",
            "time_available": "2 hours/week",
            "learning_style": "hybrid",
        },
        "skills": skills,
        "topics": [],
        "concepts": [],
        "is_default": False,
    }
    skill_payload = [{"id": f"skill-{_slugify(skill)}", "name": skill} for skill in skills]

    cypher = """
    MERGE (ps:ProjectSummary {id: $project_id})
    ON CREATE SET ps.created_at = datetime()
    SET ps.project_name = $project_name,
        ps.summary_json = $summary_json,
        ps.updated_at = datetime(),
        ps.is_default = false
    MERGE (p:Project {id: $project_id})
    ON CREATE SET p.created_at = datetime()
    SET p.name = $project_name,
        p.is_default = false,
        p.updated_at = datetime()
    MERGE (ps)-[:SUMMARY_FOR]->(p)
    WITH p
    UNWIND $skills AS skill
    MERGE (s:Skill {id: skill.id})
    ON CREATE SET s.created_at = datetime()
    SET s.name = skill.name
    MERGE (p)-[:HAS_NODE]->(s)
    RETURN p.id AS project_id
    """
    _call_query(base_url, cypher, {
        "project_id": project_id,
        "project_name": project_name,
        "summary_json": json.dumps(summary),
        "skills": skill_payload,
    })
    print(f"Created project {project_id} with skills: {', '.join(skills)}")


def _cleanup(base_url: str, project_id: str) -> None:
    cypher = """
    MATCH (ps:ProjectSummary {id: $project_id})
    OPTIONAL MATCH (ps)-[:SUMMARY_FOR]->(p:Project)
    OPTIONAL MATCH (p)-[:HAS_NODE]->(s:Skill)
    WITH ps, p, collect(distinct s) AS skills
    DETACH DELETE ps, p
    WITH skills
    UNWIND skills AS s
    OPTIONAL MATCH (s)<-[:HAS_NODE]-(:Project)
    WITH s, count(*) AS refs
    WHERE refs = 0
    DETACH DELETE s
    RETURN count(*) AS deleted_skills
    """
    _call_query(base_url, cypher, {"project_id": project_id})
    print(f"Deleted project {project_id} and unreferenced skills.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or cleanup a test project.")
    parser.add_argument("action", choices=["create", "cleanup"])
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--project-id", default="project-test-script")
    parser.add_argument("--project-name", default="Test Project (Script)")
    parser.add_argument("--skills", default="Python,Lambdas,Neo4j", help="Comma-separated skills")
    args = parser.parse_args()

    skills = [s.strip() for s in args.skills.split(",") if s.strip()]
    if not skills:
        print("Provide at least one skill.", file=sys.stderr)
        return 2

    if args.action == "create":
        _create(args.base_url, args.project_id, args.project_name, skills)
    else:
        _cleanup(args.base_url, args.project_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
