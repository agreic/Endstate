"""
Integration tests for backend services.
Tests require running Neo4j and Ollama instances.
Run with: uv run pytest tests/integration/ -v
"""
import os
import pytest

from backend.config import Config, Neo4jConfig, LLMConfig, OllamaConfig
from backend.services.knowledge_graph import KnowledgeGraphService
from backend.db.neo4j_client import Neo4jClient


def is_neo4j_available() -> bool:
    """Check if Neo4j is available for testing."""
    try:
        client = Neo4jClient()
        client.test_connection()
        return True
    except Exception:
        return False


def is_llm_available() -> bool:
    """Check if the configured LLM provider is available."""
    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "gemini":
        return bool(os.getenv("GOOGLE_API_KEY"))
    
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        import requests
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def test_config():
    """Create test configuration."""
    return Config(
        neo4j=Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password123"),
            database="neo4j",
        ),
        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "ollama"),
            ollama=OllamaConfig(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                temperature=0.0,
            ),
            # GeminiConfig handles its own API key from environment
        ),
    )


@pytest.fixture
def neo4j_client(test_config):
    """Create Neo4j client for testing."""
    client = Neo4jClient(neo4j_config=test_config.neo4j)
    yield client
    client.clean_graph()
    client.close()


@pytest.fixture
def knowledge_graph_service(test_config):
    """Create knowledge graph service for testing."""
    service = KnowledgeGraphService(app_config=test_config)
    yield service
    service.clean()
    service.close()


@pytest.mark.skipif(
    not is_neo4j_available(),
    reason="Neo4j not available - start with: docker-compose up -d neo4j",
)
class TestNeo4jClientIntegration:
    """Integration tests for Neo4j client."""

    def test_connection(self, neo4j_client):
        """Test database connection."""
        assert neo4j_client.test_connection() is True

    def test_create_and_query_nodes(self, neo4j_client):
        """Test creating and querying nodes."""
        neo4j_client.query("""
            CREATE (s:Skill {id: 'test-skill-1', name: 'Python', session_id: $session_id})
            RETURN s
        """)

        result = neo4j_client.query("MATCH (s:Skill) WHERE s.id = 'test-skill-1' AND s.session_id = $session_id RETURN s")

        assert len(result) == 1
        assert result[0]["s"]["name"] == "Python"

    def test_create_relationships(self, neo4j_client):
        """Test creating relationships."""
        neo4j_client.query("""
            CREATE (s1:Skill {id: 'skill-1', name: 'Python', session_id: $session_id})
            CREATE (s2:Skill {id: 'skill-2', name: 'Data Types', session_id: $session_id})
            CREATE (s1)-[:REQUIRES {strength: 0.8, session_id: $session_id}]->(s2)
        """)

        result = neo4j_client.query("""
            MATCH (s1:Skill)-[r:REQUIRES]->(s2:Skill)
            WHERE s1.session_id = $session_id AND s2.session_id = $session_id AND r.session_id = $session_id
            RETURN s1.name as source, r.strength as strength, s2.name as target
        """)

        assert len(result) == 1
        assert result[0]["source"] == "Python"
        assert result[0]["target"] == "Data Types"
        assert result[0]["strength"] == 0.8

    def test_get_node_count(self, neo4j_client):
        """Test getting node counts."""
        neo4j_client.query("""
            UNWIND range(1, 5) as i
            CREATE (:Skill {id: 'count-test-' + i, session_id: $session_id})
        """)

        count = neo4j_client.get_node_count("Skill")

        assert count == 5

    def test_merge_nodes_simple(self, neo4j_client):
        """Test simple node merging."""
        neo4j_client.query("""
            CREATE (s1:Skill {id: 'merge-test', name: 'Python', session_id: $session_id})
            CREATE (s2:Skill {id: 'merge-test', name: 'Python Updated', session_id: $session_id})
        """)

        deleted = neo4j_client.merge_nodes_simple("Skill", match_property="id")

        assert deleted == 1

        result = neo4j_client.query("MATCH (s:Skill) WHERE s.session_id = $session_id RETURN s")
        assert len(result) == 1

    def test_clean_by_label(self, neo4j_client):
        """Test cleaning nodes by label."""
        neo4j_client.query("""
            CREATE (:Skill {id: 'to-delete', session_id: $session_id})
            CREATE (:Concept {id: 'to-keep', session_id: $session_id})
        """)

        deleted = neo4j_client.clean_by_label("Skill")

        assert deleted == 1

        skill_count = neo4j_client.get_node_count("Skill")
        concept_count = neo4j_client.get_node_count("Concept")

        assert skill_count == 0
        assert concept_count == 1

    def test_get_graph_stats(self, neo4j_client):
        """Test getting graph statistics."""
        neo4j_client.query("""
            CREATE (s1:Skill {id: 'stat-1', session_id: $session_id})
            CREATE (s2:Skill {id: 'stat-2', session_id: $session_id})
            CREATE (s1)-[:REQUIRES {session_id: $session_id}]->(s2)
        """)

        stats = neo4j_client.get_graph_stats()

        assert stats["total_nodes"] >= 2
        assert stats["total_relationships"] >= 1
        assert "Skill" in stats["nodes"]
        assert stats["nodes"]["Skill"] == 2


@pytest.mark.skipif(
    not is_neo4j_available() or not is_llm_available(),
    reason="Neo4j and a configured LLM provider (Ollama or Gemini) are required.",
)
class TestKnowledgeGraphServiceIntegration:
    """Integration tests for knowledge graph service."""

    def test_connection_test(self, knowledge_graph_service):
        """Test connection testing."""
        results = knowledge_graph_service.test_connection()

        assert results["database"] is True
        assert results["llm"] is True

    def test_extract_and_add(self, knowledge_graph_service):
        """Test extracting knowledge and adding to graph."""
        text = "Python is a programming language that requires understanding of variables and data types."

        documents = knowledge_graph_service.extract_and_add(text)

        assert len(documents) > 0

        stats = knowledge_graph_service.get_stats()
        assert stats["total_nodes"] > 0 or stats["total_relationships"] > 0

    def test_extract_many(self, knowledge_graph_service):
        """Test extracting from multiple texts."""
        texts = [
            "Python supports object-oriented programming.",
            "JavaScript is used for web development.",
            "SQL is used for database queries.",
        ]

        documents = knowledge_graph_service.extract_many(texts)

        assert len(documents) == len(texts)

    def test_merge_duplicates(self, knowledge_graph_service):
        """Test merging duplicate nodes."""
        knowledge_graph_service.query("""
            UNWIND range(1, 3) as i
            CREATE (s:Skill {id: 'duplicate-test', name: 'Python ' + i, session_id: $session_id})
        """)

        merged = knowledge_graph_service.merge_duplicates("Skill", match_property="id")

        assert merged == 2

        stats = knowledge_graph_service.get_stats()
        assert stats["nodes"]["Skill"] == 1

    def test_custom_cypher_query(self, knowledge_graph_service):
        """Test custom Cypher queries."""
        knowledge_graph_service.query("""
            CREATE (s:Skill {id: 'query-test', name: 'Test Skill', difficulty: 'beginner', session_id: $session_id})
        """)

        result = knowledge_graph_service.query(
            "MATCH (s:Skill) WHERE s.id = $id AND s.session_id = $session_id RETURN s",
            {"id": "query-test"},
        )

        assert len(result) == 1
        assert result[0]["s"]["difficulty"] == "beginner"

    def test_get_nodes_and_relationships(self, knowledge_graph_service):
        """Test getting nodes and relationships."""
        knowledge_graph_service.query("""
            CREATE (s1:Skill {id: 'get-test-1', session_id: $session_id})
            CREATE (s2:Skill {id: 'get-test-2', session_id: $session_id})
            CREATE (s1)-[:REQUIRES {session_id: $session_id}]->(s2)
        """)

        nodes = knowledge_graph_service.get_nodes("Skill")
        rels = knowledge_graph_service.get_relationships()

        assert len(nodes) >= 2
        assert len(rels) >= 1


@pytest.mark.skipif(
    not is_llm_available(),
    reason="Configured LLM provider not available.",
)
class TestLLMIntegration:
    """Integration tests for the configured LLM."""

    def test_llm_connection(self, test_config):
        """Test LLM connection."""
        from backend.llm.provider import get_llm, test_llm

        llm = get_llm(llm_config=test_config.llm)
        success, message = test_llm(llm)

        assert success is True
        assert len(message) > 0

    def test_llm_extraction(self, knowledge_graph_service):
        """Test knowledge extraction with configured LLM."""
        text = "Machine learning is a subset of artificial intelligence."

        documents = knowledge_graph_service.extract(text)

        assert len(documents) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
