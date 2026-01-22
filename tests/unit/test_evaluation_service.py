from backend.services.evaluation_service import build_project_brief, derive_required_skills


def test_build_project_brief_handles_missing_fields():
    summary = {"agreed_project": {"name": "Test Project", "description": "Learn X"}}
    brief = build_project_brief(summary)
    assert "Test Project" in brief
    assert "Learn X" in brief


def test_derive_required_skills_prefers_summary():
    summary = {"skills": ["Python", "Neo4j"]}
    skills = derive_required_skills(summary, ["Fallback"])
    assert skills == ["Python", "Neo4j"]


def test_derive_required_skills_fallbacks_to_skill_nodes():
    summary = {"skills": []}
    skills = derive_required_skills(summary, ["Python", "Neo4j"])
    assert skills == ["Python", "Neo4j"]
