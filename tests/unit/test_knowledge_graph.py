"""
Unit tests for knowledge graph service.
Tests service layer combining LLM and database operations.
"""
from unittest.mock import patch, MagicMock

from backend.services.knowledge_graph import KnowledgeGraphService
from backend.config import Config, Neo4jConfig, LLMConfig


class TestKnowledgeGraphServiceInit:
    """Tests for KnowledgeGraphService initialization."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_default_initialization(
        self, mock_transformer, mock_get_llm, mock_neo4j_client
    ):
        """Test initialization with default configuration."""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db

        service = KnowledgeGraphService()

        mock_get_llm.assert_called_once()
        mock_neo4j_client.assert_called_once()
        assert service._llm == mock_llm
        assert service._db == mock_db

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_custom_llm_provider(
        self, mock_transformer, mock_get_llm, mock_neo4j_client
    ):
        """Test initialization with custom LLM provider."""
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db

        service = KnowledgeGraphService(llm_provider="ollama")

        call_kwargs = mock_get_llm.call_args[1]
        assert call_kwargs["provider"] == "ollama"

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_custom_llm_instance(
        self, mock_transformer, mock_get_llm, mock_neo4j_client
    ):
        """Test initialization with custom LLM instance."""
        custom_llm = MagicMock()
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db

        service = KnowledgeGraphService(llm=custom_llm)

        mock_get_llm.assert_not_called()
        assert service._llm == custom_llm

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_custom_config(
        self, mock_transformer, mock_get_llm, mock_neo4j_client
    ):
        """Test initialization with custom configuration."""
        custom_config = Config(
            neo4j=Neo4jConfig(uri="bolt://custom:7687"),
            llm=LLMConfig(provider="ollama"),
        )
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db

        service = KnowledgeGraphService(app_config=custom_config)

        mock_neo4j_client.assert_called_once_with(custom_config.neo4j)
        call_kwargs = mock_get_llm.call_args[1]
        assert call_kwargs["llm_config"] == custom_config.llm


class TestKnowledgeGraphServiceProperties:
    """Tests for KnowledgeGraphService property accessors."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_db_property(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test db property returns database client."""
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        service = KnowledgeGraphService()

        assert service.db == mock_db

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_transformer_property(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """test transformer property returns graph transformer."""
        mock_transformer_instance = MagicMock()
        mock_transformer.return_value = mock_transformer_instance
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        service = KnowledgeGraphService()

        assert service.transformer == mock_transformer_instance

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_schema_property(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test schema property returns current schema."""
        mock_schema = MagicMock()
        mock_transformer_instance = MagicMock()
        mock_transformer_instance.schema = mock_schema
        mock_transformer.return_value = mock_transformer_instance
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        service = KnowledgeGraphService()

        assert service.schema == mock_schema

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_schema_setter(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test schema property setter."""
        mock_transformer_instance = MagicMock()
        mock_transformer.return_value = mock_transformer_instance
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_new_schema = MagicMock()

        service = KnowledgeGraphService()

        service.schema = mock_new_schema

        assert mock_transformer_instance.schema == mock_new_schema


class TestKnowledgeGraphServiceTestConnection:
    """Tests for test_connection method."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    @patch("backend.llm.provider.test_llm")
    def test_test_connection_success(
        self, mock_test_llm, mock_transformer, mock_get_llm, mock_neo4j_client
    ):
        """Test successful connection test."""
        mock_db = MagicMock()
        mock_db.test_connection.return_value = True
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_test_llm.return_value = (True, "Hello")

        service = KnowledgeGraphService()

        result = service.test_connection()

        assert result["database"] is True
        assert result["llm"] is True
        assert result["database_error"] is None
        assert result["llm_error"] is None


class TestKnowledgeGraphServiceMergeGuard:
    """Tests for merge guard to prevent non-KG merges."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_merge_duplicates_rejects_project(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        service = KnowledgeGraphService()

        try:
            service.merge_duplicates("Project", match_property="name")
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "Merge is only allowed" in str(exc)

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    @patch("backend.llm.provider.test_llm")
    def test_test_connection_db_failure(
        self, mock_test_llm, mock_transformer, mock_get_llm, mock_neo4j_client
    ):
        """Test connection test with database failure."""
        mock_db = MagicMock()
        mock_db.test_connection.side_effect = Exception("Connection refused")
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_test_llm.return_value = (True, "Hello")

        service = KnowledgeGraphService()

        result = service.test_connection()

        assert result["database"] is False
        assert "Connection refused" in result["database_error"]
        assert result["llm"] is True

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    @patch("backend.llm.provider.test_llm")
    def test_test_connection_llm_failure(
        self, mock_test_llm, mock_transformer, mock_get_llm, mock_neo4j_client
    ):
        """Test connection test with LLM failure."""
        mock_db = MagicMock()
        mock_db.test_connection.return_value = True
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_test_llm.return_value = (False, "Model not found")

        service = KnowledgeGraphService()

        result = service.test_connection()

        assert result["database"] is True
        assert result["llm"] is False
        assert "Model not found" in result["llm_error"]


class TestKnowledgeGraphServiceExtract:
    """Tests for extraction methods."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_extract(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test text extraction."""
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer_instance = MagicMock()
        mock_transformer_instance.process_text.return_value = [{"nodes": [], "rels": []}]
        mock_transformer.return_value = mock_transformer_instance

        service = KnowledgeGraphService()

        result = service.extract("Python is a programming language")

        mock_transformer_instance.process_text.assert_called_once_with(
            "Python is a programming language"
        )
        assert result == [{"nodes": [], "rels": []}]

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_extract_many(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test multiple text extraction."""
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer_instance = MagicMock()
        mock_transformer_instance.process_texts.return_value = [{"nodes": []}]
        mock_transformer.return_value = mock_transformer_instance

        service = KnowledgeGraphService()

        texts = ["Text 1", "Text 2"]
        _ = service.extract_many(texts)

        mock_transformer_instance.process_texts.assert_called_once_with(texts)


class TestKnowledgeGraphServiceAddDocuments:
    """Tests for add_documents method."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_add_documents(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test adding documents to database."""
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        mock_doc = MagicMock()
        mock_doc.nodes = []
        documents = [mock_doc]
        service.add_documents(documents, include_source=True, base_entity_label=True, normalize=False)

        mock_db.add_graph_documents.assert_called_once_with(
            documents, include_source=True, base_entity_label=True
        )


class TestKnowledgeGraphServiceExtractAndAdd:
    """Tests for extract_and_add method."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_extract_and_add(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test extract and add in one step."""
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer_instance = MagicMock()
        mock_doc = MagicMock()
        mock_doc.nodes = []
        mock_documents = [mock_doc]
        mock_transformer_instance.process_text.return_value = mock_documents
        mock_transformer.return_value = mock_transformer_instance

        service = KnowledgeGraphService()

        result = service.extract_and_add("Python is great")

        mock_transformer_instance.process_text.assert_called_once_with("Python is great")
        mock_db.add_graph_documents.assert_called_once_with(
            mock_documents, include_source=False, base_entity_label=True
        )
        assert result == mock_documents


class TestKnowledgeGraphServiceClean:
    """Tests for graph cleaning methods."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_clean(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test cleaning entire graph."""
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        service.clean()

        mock_db.clean_graph.assert_called_once()

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_clean_by_label(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test cleaning nodes by label."""
        mock_db = MagicMock()
        mock_db.clean_by_label.return_value = 5
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        deleted = service.clean_by_label("Skill")

        mock_db.clean_by_label.assert_called_once_with("Skill")
        assert deleted == 5


class TestKnowledgeGraphServiceMergeDuplicates:
    """Tests for merge duplicate methods."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_merge_duplicates_success(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test successful merge of duplicates."""
        mock_db = MagicMock()
        mock_db.merge_nodes.return_value = 3
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        merged = service.merge_duplicates("Skill", match_property="id")

        mock_db.merge_nodes.assert_called_once_with("Skill", "id")
        assert merged == 3

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_merge_duplicates_fallback(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test fallback to simple merge when APOC unavailable."""
        mock_db = MagicMock()
        mock_db.merge_nodes.side_effect = Exception("APOC not available")
        mock_db.merge_nodes_simple.return_value = 2
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        merged = service.merge_duplicates("Skill")

        mock_db.merge_nodes.assert_called_once_with("Skill", "id")
        mock_db.merge_nodes_simple.assert_called_once_with("Skill", "id")
        assert merged == 2

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_merge_all_duplicates(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test merging duplicates for all schema labels."""
        mock_db = MagicMock()
        mock_db.merge_nodes.return_value = 2
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer_instance = MagicMock()
        mock_schema = MagicMock()
        mock_schema.allowed_nodes = ["Skill", "Concept", "Topic"]
        mock_transformer_instance.schema = mock_schema
        mock_transformer.return_value = mock_transformer_instance

        service = KnowledgeGraphService()

        results = service.merge_all_duplicates()

        assert mock_db.merge_nodes.call_count == 3
        assert "Skill" in results
        assert "Concept" in results
        assert "Topic" in results


class TestKnowledgeGraphServiceQuery:
    """Tests for custom query methods."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_query(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test custom Cypher query execution."""
        mock_db = MagicMock()
        mock_db.query.return_value = [{"id": 1}]
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        _ = service.query("MATCH (n) RETURN n LIMIT 1")

        mock_db.query.assert_called_once_with("MATCH (n) RETURN n LIMIT 1", None)

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_query_with_params(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test custom query with parameters."""
        mock_db = MagicMock()
        mock_db.query.return_value = [{"name": "Python"}]
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        result = _ = service.query("MATCH (n:Skill WHERE n.id = $id) RETURN n", {"id": "test"})

        mock_db.query.assert_called_once_with(
            "MATCH (n:Skill WHERE n.id = $id) RETURN n", {"id": "test"}
        )


class TestKnowledgeGraphServiceStats:
    """Tests for statistics methods."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_get_stats(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test getting graph statistics."""
        mock_db = MagicMock()
        mock_db.get_graph_stats.return_value = {
            "total_nodes": 10,
            "total_relationships": 5,
        }
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        stats = service.get_stats()

        mock_db.get_graph_stats.assert_called_once()
        assert stats["total_nodes"] == 10
        assert stats["total_relationships"] == 5

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_get_nodes(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test getting nodes from graph."""
        mock_db = MagicMock()
        mock_db.get_all_nodes.return_value = [{"id": "1"}, {"id": "2"}]
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        nodes = service.get_nodes(label="Skill", limit=50)

        mock_db.get_all_nodes.assert_called_once_with("Skill", 50)

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_get_relationships(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test getting relationships from graph."""
        mock_db = MagicMock()
        mock_db.get_all_relationships.return_value = [{"type": "REQUIRES"}]
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        rels = service.get_relationships(limit=10)

        mock_db.get_all_relationships.assert_called_once_with(10)


class TestKnowledgeGraphServiceClose:
    """Tests for close and context manager."""

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_close(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test close method."""
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        service = KnowledgeGraphService()

        service.close()

        mock_db.close.assert_called_once()

    @patch("backend.services.knowledge_graph.Neo4jClient")
    @patch("backend.services.knowledge_graph.get_llm")
    @patch("backend.services.knowledge_graph.GraphTransformer")
    def test_context_manager(self, mock_transformer, mock_get_llm, mock_neo4j_client):
        """Test context manager protocol."""
        mock_db = MagicMock()
        mock_neo4j_client.return_value = mock_db
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_transformer = MagicMock()
        mock_transformer.return_value = MagicMock()

        with KnowledgeGraphService() as service:
            assert service._db == mock_db

        mock_db.close.assert_called_once()
