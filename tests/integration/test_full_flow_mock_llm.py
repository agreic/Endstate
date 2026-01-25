import pytest
import asyncio
import json
import uuid
from unittest.mock import MagicMock, patch

from backend.config import Config, Neo4jConfig
from backend.db.neo4j_client import Neo4jClient
from backend.services.chat_service import chat_service
from backend.services.lesson_service import generate_and_store_lesson
from backend.services.assessment_service import generate_assessment, evaluate_assessment
from backend.services.evaluation_service import evaluate_submission

# --- Mock LLM ---

class MockLLMResponse:
    def __init__(self, content):
        self.content = content

class MockLLM:
    def __init__(self):
        self.call_history = []

    async def ainvoke(self, messages):
        self.call_history.append(messages)
        prompt = messages[-1][1] if isinstance(messages[-1], tuple) else messages[-1].content
        
        # 1. Project Suggestions
        if "curriculum architect" in prompt.lower() or ("json schema" in prompt.lower() and "projects" in prompt.lower()):
            return MockLLMResponse(json.dumps({
                "projects": [
                    {
                        "title": "Mock Project Alpha",
                        "description": "A mock project for testing.",
                        "difficulty": "Beginner",
                        "tags": ["Python", "Mocking"]
                    },
                    {
                        "title": "Mock Project Beta",
                        "description": "Another mock project.",
                        "difficulty": "Intermediate",
                        "tags": ["Testing", "Automation"]
                    },
                    {
                        "title": "Mock Project Gamma",
                        "description": "A third mock project.",
                        "difficulty": "Advanced",
                        "tags": ["AI", "MockLLM"]
                    }
                ]
            }))
        
        # 3. Assessment Generation (Check BEFORE Lesson because prompt includes lesson content)
        if "create one assessment prompt" in prompt.lower():
            return MockLLMResponse(json.dumps({
                "prompt": "What is the capital of Mockland?"
            }))
        
        # 2. Lesson Generation
        if "create a short, focused lesson" in prompt.lower():
            return MockLLMResponse(json.dumps({
                "explanation": "This is a mock lesson explanation. It covers the core concept.",
                "task": "Read the documentation."
            }))
            
        # 4. Assessment Evaluation
        if "evaluate the learner's answer" in prompt.lower():
            return MockLLMResponse(json.dumps({
                "result": "pass",
                "feedback": "Correct answer!"
            }))

        # 5. Capstone Evaluation
        if "capstone" in prompt.lower() or ("rubric" in prompt.lower() and "submission" in prompt.lower()):
             return MockLLMResponse(json.dumps({
                "score": 0.95,
                "criteria": {"Skill Application": "Excellent"},
                "skill_evidence": {"Python": "Demonstrated"},
                "overall_feedback": "Great job on the mock project!",
                "suggestions": ["Add more tests"],
                "passed": True
            }))

        # 6. Project Alignment 
        if "alignment" in prompt.lower() or "user goal" in prompt.lower():
             return MockLLMResponse(json.dumps({
                "score": 0.8,
                "critique": "Aligned well."
            }))

        # 7. KG Quality
        if "kg quality" in prompt.lower():
             return MockLLMResponse(json.dumps({
                "coverage_score": 0.9,
                "redundancy_score": 0.1,
                "critique": "Solid graph."
            }))
            
        # Default Chat
        return MockLLMResponse("This is a mock response from the AI.")

# --- Fixtures ---

@pytest.fixture(scope="module")
def mock_config():
    return Config(
        neo4j=Neo4jConfig(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password123", # Assuming default local credentials for demo/test
            database="neo4j",
        )
    )

@pytest.fixture
def mock_llm():
    return MockLLM()

@pytest.fixture
def override_get_llm(mock_llm):
    with patch("backend.services.chat_service.get_llm", return_value=mock_llm), \
         patch("backend.services.lesson_service.get_llm", return_value=mock_llm), \
         patch("backend.services.assessment_service.get_llm", return_value=mock_llm), \
         patch("backend.services.evaluation_service.get_llm", return_value=mock_llm):
        yield mock_llm

@pytest.fixture
def db_client(mock_config):
    client = Neo4jClient(neo4j_config=mock_config.neo4j)
    if not client.test_connection():
        pytest.skip("Neo4j not available")
    yield client
    client.clean_graph() # Clean up after test
    client.close()

# --- Integration Tests ---

@pytest.mark.asyncio
async def test_full_user_flow_mocked(db_client, override_get_llm, mock_llm):
    session_id = f"test-session-{uuid.uuid4()}"
    
    # 1. Chat Interaction
    print("\n--- Step 1: Chat ---")
    response = await chat_service.send_message(session_id, "I want to learn Python testing", str(uuid.uuid4()))
    assert response.success is True
    assert response.content == "This is a mock response from the AI."
    
    # 2. Request Project Suggestions
    print("\n--- Step 2: Suggestions ---")
    suggestions = await chat_service.request_project_suggestions(session_id)
    # The actual implementation puts it in background/DB, so we check the result directly or wait
    # For test simplicity, we can use the direct generator if public, or check pending proposals
    # The service method request_project_suggestions runs in background.
    # We should use request_project_suggestions_from_history with store=False for sync check, 
    # OR wait for background task.
    # Let's call the internal generator directly to be synchronous for testing logic
    history = chat_service.get_messages(session_id)
    proposals = await chat_service.generate_project_suggestions_from_history(session_id, history, store=True)
    
    assert len(proposals) == 3
    assert proposals[0]["title"] == "Mock Project Alpha"
    
    # 3. Accept Project
    print("\n--- Step 3: Accept Project ---")
    proposal_id = proposals[0]["id"]
    result = await chat_service.accept_project_proposal(session_id, proposal_id)
    project_id = result["project_id"]
    assert project_id is not None
    
    # Verify project exists
    from backend.config import X_SESSION_ID
    
    # Set context var to match session_id used in creation
    token = X_SESSION_ID.set(session_id)
    try:
        project = db_client.get_project_summary(project_id)
        assert project is not None
        assert project[0]["name"] == "Mock Project Alpha"
    finally:
        X_SESSION_ID.reset(token)
    
    # 4. Lesson Generation
    print("\n--- Step 4: Lesson ---")
    # First ensure we have nodes (the accept_project usually generates graph nodes via layout_service or graph_service)
    # In strict mock mode, graph generation might be skipped if it relies on LLM in a way we mocked incompletely.
    # Let's inspect if graph nodes exist. 
    nodes = db_client.list_project_nodes(project_id)
    # If nodes are empty (because strict LLM graph generation wasn't fully mocked or triggered here), 
    # we manually create a node to test lesson generation
    if not nodes:
        db_client.query("CREATE (n:Skill {id: 'mock-skill', name: 'Mock Skill', project_id: $pid})", {"pid": project_id})
        node_id = "mock-skill"
    else:
        node_id = nodes[0]["id"]
        
    lesson = await generate_and_store_lesson(db_client, project_id, {"id": node_id, "labels": ["Skill"], "properties": {"name": "Mock Skill"}}, None, 1, [])
    assert lesson["explanation"] == "This is a mock lesson explanation. It covers the core concept."
    lesson_id = lesson["lesson_id"]
    
    # 5. Assessment
    print("\n--- Step 5: Assessment ---")
    assessment = await generate_assessment(lesson, None)
    assert assessment["prompt"] == "What is the capital of Mockland?"
    
    # Evaluate Assessment
    eval_result = await evaluate_assessment(lesson, assessment, "I don't know")
    assert eval_result["result"] == "pass" # Because mock returns pass regardless of answer
    
    # 6. Capstone Submission
    print("\n--- Step 6: Capstone ---")
    submission_content = "Here is my project code."
    # We need to call the service that handles submission
    capstone_result = await evaluate_submission(submission_content, "Brief", ["Python"], "mock-model")
    
    assert capstone_result["score"] == 0.95
    assert capstone_result["passed"] is True
    
    print("\n--- Full Flow Complete ---")

if __name__ == "__main__":
    # Allow running directly `python tests/integration/test_full_flow_mock_llm.py`
    import sys
    sys.exit(pytest.main(["-v", __file__]))
