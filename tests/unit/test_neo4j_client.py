"""
Unit tests for Neo4j client module.
Tests database operations including merge functions.
"""
from unittest.mock import patch, MagicMock, PropertyMock
import pytest

from backend.db.neo4j_client import Neo4jClient
from backend.config import Neo4jConfig


class TestNeo4jClientInit:
    """Tests for Neo4jClient initialization."""

    def test_default_initialization(self):
        """Test initialization with default config."""
        with patch("backend.db.neo4j_client.config") as mock_config:
            mock_config.neo4j = Neo4jConfig(
                _uri="bolt://localhost:7687",
                _username="neo4j",
                _password="password",
                database="neo4j",
            )

            client = Neo4jClient()

            assert client._config == mock_config.neo4j
            assert client._graph is None
            assert client._driver is None

    def test_custom_config_initialization(self):
        """Test initialization with custom config."""
        custom_config = Neo4jConfig(
            _uri="bolt://custom:7687",
            _username="admin",
            _password="secret",
            database="testdb",
        )

        client = Neo4jClient(neo4j_config=custom_config)

        assert client._config.uri == "bolt://custom:7687"
        assert client._config.username == "admin"
        assert client._config.password == "secret"
        assert client._config.database == "testdb"


class TestNeo4jClientGraph:
    """Tests for Neo4jClient graph property."""

    @patch("backend.db.neo4j_client.Neo4jGraph")
    def test_graph_creates_instance(self, mock_neo4j_graph):
        """Test that graph property creates Neo4jGraph instance."""
        mock_graph = MagicMock()
        mock_neo4j_graph.return_value = mock_graph

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        graph = client.graph

        mock_neo4j_graph.assert_called_once_with(
            url="bolt://localhost:7687",
            username="neo4j",
            password="password123",
            database="neo4j",
            refresh_schema=False,
        )
        assert graph == mock_graph

    @patch("backend.db.neo4j_client.Neo4jGraph")
    def test_graph_returns_cached_instance(self, mock_neo4j_graph):
        """Test that graph property returns cached instance."""
        mock_graph = MagicMock()
        mock_neo4j_graph.return_value = mock_graph

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        graph1 = client.graph
        graph2 = client.graph

        assert mock_neo4j_graph.call_count == 1
        assert graph1 == graph2


class TestNeo4jClientDriver:
    """Tests for Neo4jClient driver property."""

    @patch("backend.db.neo4j_client.GraphDatabase")
    def test_driver_creates_instance(self, mock_graph_db):
        """Test that driver property creates GraphDatabase driver."""
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        driver = client.driver

        mock_graph_db.driver.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "password123"),
        )
        assert driver == mock_driver


class TestNeo4jClientTestConnection:
    """Tests for test_connection method."""

    @patch.object(Neo4jClient, "graph", new_callable=PropertyMock)
    def test_test_connection_success(self, mock_graph_prop):
        """Test successful connection test."""
        mock_graph = MagicMock()
        mock_graph.query.return_value = [{"test": 1}]
        mock_graph_prop.return_value = mock_graph

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        result = client.test_connection()

        assert result is True
        mock_graph.query.assert_called_once_with("RETURN 1 as test")

    @patch.object(Neo4jClient, "graph", new_callable=PropertyMock)
    def test_test_connection_failure(self, mock_graph_prop):
        """Test failed connection test."""
        mock_graph = MagicMock()
        mock_graph.query.side_effect = Exception("Connection refused")
        mock_graph_prop.return_value = mock_graph

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        with pytest.raises(ConnectionError, match="Failed to connect to Neo4j"):
            client.test_connection()


class TestNeo4jClientQuery:
    """Tests for query method."""

    @patch.object(Neo4jClient, "graph", new_callable=PropertyMock)
    def test_query_with_params(self, mock_graph_prop):
        """Test query with parameters."""
        mock_graph = MagicMock()
        mock_graph.query.return_value = [{"id": 1, "name": "test"}]
        mock_graph_prop.return_value = mock_graph

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        result = client.query("MATCH (n) WHERE n.id = $id RETURN n", {"id": 1})

        mock_graph.query.assert_called_once_with(
            "MATCH (n) WHERE n.id = $id RETURN n",
            {"id": 1},
        )
        assert result == [{"id": 1, "name": "test"}]

    @patch.object(Neo4jClient, "graph", new_callable=PropertyMock)
    def test_query_without_params(self, mock_graph_prop):
        """Test query without parameters."""
        mock_graph = MagicMock()
        mock_graph.query.return_value = [{"count": 5}]
        mock_graph_prop.return_value = mock_graph

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        client.query("MATCH (n) RETURN count(n) as count")

        mock_graph.query.assert_called_once_with(
            "MATCH (n) RETURN count(n) as count",
            {},
        )


class TestNeo4jClientCleanGraph:
    """Tests for clean_graph method."""

    @patch.object(Neo4jClient, "query")
    def test_clean_graph(self, mock_query):
        """Test cleaning entire graph."""
        mock_query.return_value = []

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        client.clean_graph()

        mock_query.assert_called_once_with("MATCH (n) DETACH DELETE n")


class TestNeo4jClientCleanByLabel:
    """Tests for clean_by_label method."""

    @patch.object(Neo4jClient, "query")
    def test_clean_by_label_with_nodes(self, mock_query):
        """Test cleaning nodes with specific label."""
        mock_query.return_value = [{"deleted": 5}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        deleted = client.clean_by_label("Skill")

        mock_query.assert_called_once_with(
            "MATCH (n:Skill) DETACH DELETE n RETURN count(n) as deleted"
        )
        assert deleted == 5

    @patch.object(Neo4jClient, "query")
    def test_clean_by_label_no_nodes(self, mock_query):
        """Test cleaning with no matching nodes."""
        mock_query.return_value = []

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        deleted = client.clean_by_label("NonExistent")

        assert deleted == 0

    @patch.object(Neo4jClient, "query")
    def test_clean_by_label_empty_result(self, mock_query):
        """Test cleaning with empty result list."""
        mock_query.return_value = []

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        deleted = client.clean_by_label("Skill")

        assert deleted == 0


class TestNeo4jClientAddGraphDocuments:
    """Tests for add_graph_documents method."""

    @patch.object(Neo4jClient, "graph", new_callable=PropertyMock)
    def test_add_graph_documents(self, mock_graph_prop):
        """Test adding graph documents."""
        mock_graph = MagicMock()
        mock_graph_prop.return_value = mock_graph

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        documents = [{"nodes": [], "relationships": []}]
        client.add_graph_documents(documents, include_source=False, base_entity_label=True)

        mock_graph.add_graph_documents.assert_called_once_with(
            documents,
            include_source=False,
            baseEntityLabel=True,
        )


class TestNeo4jClientMergeNodes:
    """Tests for merge_nodes method (APOC-based)."""

    @patch.object(Neo4jClient, "query")
    def test_merge_nodes_success(self, mock_query):
        """Test successful node merge."""
        mock_query.return_value = [{"total_merged": 3}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        merged = client.merge_nodes("Skill", match_property="id")

        assert merged == 3
        assert "MATCH (n:Skill)" in mock_query.call_args[0][0]
        assert "apoc.create.relationship" in mock_query.call_args[0][0]

    @patch.object(Neo4jClient, "query")
    def test_merge_nodes_no_duplicates(self, mock_query):
        """Test merge with no duplicate nodes."""
        mock_query.return_value = [{"total_merged": 0}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        merged = client.merge_nodes("Skill")

        assert merged == 0

    @patch.object(Neo4jClient, "query")
    def test_merge_nodes_empty_result(self, mock_query):
        """Test merge with empty result."""
        mock_query.return_value = []

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        merged = client.merge_nodes("Skill")

        assert merged == 0

    @patch.object(Neo4jClient, "query")
    def test_merge_nodes_with_custom_property(self, mock_query):
        """Test merge using custom match property."""
        mock_query.return_value = [{"total_merged": 1}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        client.merge_nodes("Concept", match_property="name")

        query = mock_query.call_args[0][0]
        assert "n.name AS prop" in query


class TestNeo4jClientMergeNodesSimple:
    """Tests for merge_nodes_simple method (non-APOC)."""

    @patch.object(Neo4jClient, "query")
    def test_merge_nodes_simple_success(self, mock_query):
        """Test simple node merge."""
        mock_query.side_effect = [
            [{"keep_id": "keep-1", "dup_ids": ["dup-1", "dup-2"]}],
            [],
            [],
            [],
            [],
            [],
            [],
        ]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        deleted = client.merge_nodes_simple("Skill")

        assert deleted == 2
        assert "elementId" in mock_query.call_args_list[0][0][0]

    @patch.object(Neo4jClient, "query")
    def test_merge_nodes_simple_no_duplicates(self, mock_query):
        """Test simple merge with no duplicates."""
        mock_query.return_value = []

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        deleted = client.merge_nodes_simple("Skill")

        assert deleted == 0

    @patch.object(Neo4jClient, "query")
    def test_merge_nodes_simple_empty_result(self, mock_query):
        """Test simple merge with empty result."""
        mock_query.return_value = []

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        deleted = client.merge_nodes_simple("Skill")

        assert deleted == 0


class TestNeo4jClientGetNodeCount:
    """Tests for get_node_count method."""

    @patch.object(Neo4jClient, "query")
    def test_get_node_count_all(self, mock_query):
        """Test getting count of all nodes."""
        mock_query.return_value = [{"count": 100}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        count = client.get_node_count()

        mock_query.assert_called_once_with("MATCH (n) RETURN count(n) as count")
        assert count == 100

    @patch.object(Neo4jClient, "query")
    def test_get_node_count_with_label(self, mock_query):
        """Test getting count with label filter."""
        mock_query.return_value = [{"count": 25}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        count = client.get_node_count("Skill")

        mock_query.assert_called_once_with(
            "MATCH (n:Skill) RETURN count(n) as count"
        )
        assert count == 25

    @patch.object(Neo4jClient, "query")
    def test_get_node_count_empty_result(self, mock_query):
        """Test getting count with empty result."""
        mock_query.return_value = []

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        count = client.get_node_count()

        assert count == 0


class TestNeo4jClientGetRelationshipCount:
    """Tests for get_relationship_count method."""

    @patch.object(Neo4jClient, "query")
    def test_get_relationship_count_all(self, mock_query):
        """Test getting count of all relationships."""
        mock_query.return_value = [{"count": 50}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        count = client.get_relationship_count()

        mock_query.assert_called_once_with(
            "MATCH ()-[r]->() RETURN count(r) as count"
        )
        assert count == 50

    @patch.object(Neo4jClient, "query")
    def test_get_relationship_count_with_type(self, mock_query):
        """Test getting count with relationship type filter."""
        mock_query.return_value = [{"count": 10}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        count = client.get_relationship_count("REQUIRES")

        mock_query.assert_called_once_with(
            "MATCH ()-[r:REQUIRES]->() RETURN count(r) as count"
        )
        assert count == 10


class TestNeo4jClientGetGraphStats:
    """Tests for get_graph_stats method."""

    @patch.object(Neo4jClient, "query")
    @patch.object(Neo4jClient, "get_node_count")
    @patch.object(Neo4jClient, "get_relationship_count")
    def test_get_graph_stats(self, mock_rel_count, mock_node_count, mock_query):
        """Test getting graph statistics."""
        mock_query.side_effect = [
            [{"label": "Skill", "count": 10}, {"label": "Concept", "count": 5}],
            [{"relationshipType": "REQUIRES", "count": 8}, {"relationshipType": "RELATED_TO", "count": 3}],
        ]
        mock_node_count.return_value = 15
        mock_rel_count.return_value = 11

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        stats = client.get_graph_stats()

        assert stats["total_nodes"] == 15
        assert stats["total_relationships"] == 11
        assert stats["nodes"]["Skill"] == 10
        assert stats["nodes"]["Concept"] == 5
        assert stats["relationships"]["REQUIRES"] == 8
        assert stats["relationships"]["RELATED_TO"] == 3

    @patch.object(Neo4jClient, "query")
    @patch.object(Neo4jClient, "get_node_count")
    @patch.object(Neo4jClient, "get_relationship_count")
    def test_get_graph_stats_empty(self, mock_rel_count, mock_node_count, mock_query):
        """Test getting stats from empty graph."""
        mock_query.side_effect = [[], []]
        mock_node_count.return_value = 0
        mock_rel_count.return_value = 0

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        stats = client.get_graph_stats()

        assert stats["nodes"] == {}
        assert stats["relationships"] == {}
        assert stats["total_nodes"] == 0
        assert stats["total_relationships"] == 0


class TestNeo4jClientGetAllNodes:
    """Tests for get_all_nodes method."""

    @patch.object(Neo4jClient, "query")
    def test_get_all_nodes_no_filter(self, mock_query):
        """Test getting all nodes without label filter."""
        mock_query.return_value = [{"n": {"id": "1"}}, {"n": {"id": "2"}}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        nodes = client.get_all_nodes()

        mock_query.assert_called_once_with("MATCH (n) RETURN n LIMIT 100")
        assert len(nodes) == 2

    @patch.object(Neo4jClient, "query")
    def test_get_all_nodes_with_label(self, mock_query):
        """Test getting nodes with label filter."""
        mock_query.return_value = [{"n": {"id": "1"}}]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        nodes = client.get_all_nodes("Skill")

        mock_query.assert_called_once_with("MATCH (n:Skill) RETURN n LIMIT 100")
        assert len(nodes) == 1

    @patch.object(Neo4jClient, "query")
    def test_get_all_nodes_with_limit(self, mock_query):
        """Test getting nodes with custom limit."""
        mock_query.return_value = []

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        client.get_all_nodes(limit=50)

        mock_query.assert_called_once_with("MATCH (n) RETURN n LIMIT 50")


class TestNeo4jClientGetAllRelationships:
    """Tests for get_all_relationships method."""

    @patch.object(Neo4jClient, "query")
    def test_get_all_relationships(self, mock_query):
        """Test getting all relationships."""
        mock_query.return_value = [
            {"source": "1", "type": "REQUIRES", "target": "2", "properties": {}},
        ]

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        rels = client.get_all_relationships()

        assert len(rels) == 1
        assert rels[0]["source"] == "1"
        assert rels[0]["type"] == "REQUIRES"
        assert rels[0]["target"] == "2"

    @patch.object(Neo4jClient, "query")
    def test_get_all_relationships_with_limit(self, mock_query):
        """Test getting relationships with limit."""
        mock_query.return_value = []

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        client.get_all_relationships(limit=50)

        mock_query.assert_called_once()
        assert "LIMIT 50" in mock_query.call_args[0][0]


class TestNeo4jClientClose:
    """Tests for close method."""

    @patch.object(Neo4jClient, "graph", new_callable=PropertyMock)
    def test_close_with_driver(self, mock_graph_prop):
        """Test closing client with active driver."""
        mock_driver = MagicMock()
        mock_graph = MagicMock()
        mock_graph_prop.return_value = mock_graph

        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)
        client._driver = mock_driver

        client.close()

        mock_driver.close.assert_called_once()
        assert client._driver is None
        assert client._graph is None

    def test_close_without_driver(self):
        """Test closing client without active driver."""
        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        client.close()

        assert client._driver is None
        assert client._graph is None


class TestNeo4jClientContextManager:
    """Tests for context manager protocol."""

    @patch.object(Neo4jClient, "graph", new_callable=PropertyMock)
    @patch.object(Neo4jClient, "close")
    def test_context_manager_enter(self, mock_close, mock_graph_prop):
        """Test context manager entry."""
        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        with client as entered:
            assert entered == client

    @patch.object(Neo4jClient, "graph", new_callable=PropertyMock)
    @patch.object(Neo4jClient, "close")
    def test_context_manager_exit(self, mock_close, mock_graph_prop):
        """Test context manager exit does NOT close connection (connection pool manages lifecycle)."""
        config = Neo4jConfig()
        client = Neo4jClient(neo4j_config=config)

        with client:
            pass

        mock_close.assert_not_called()


class TestNeo4jClientLessonAssessment:
    """Tests for lesson and assessment persistence helpers."""

    @patch.object(Neo4jClient, "query")
    def test_archive_project_lesson(self, mock_query):
        client = Neo4jClient()

        client.archive_project_lesson("proj-1", "lesson-1")

        mock_query.assert_called_once()
        query, params = mock_query.call_args[0]
        assert "ProjectLesson" in query
        assert params == {"project_id": "proj-1", "lesson_id": "lesson-1"}

    @patch.object(Neo4jClient, "query")
    def test_delete_project_lesson(self, mock_query):
        client = Neo4jClient()

        client.delete_project_lesson("proj-1", "lesson-1")

        mock_query.assert_called_once()
        query, params = mock_query.call_args[0]
        assert "DETACH DELETE l" in query
        assert params == {"project_id": "proj-1", "lesson_id": "lesson-1"}

    @patch.object(Neo4jClient, "query")
    def test_archive_project_assessment(self, mock_query):
        client = Neo4jClient()

        client.archive_project_assessment("proj-1", "assessment-1")

        mock_query.assert_called_once()
        query, params = mock_query.call_args[0]
        assert "ProjectAssessment" in query
        assert params == {"project_id": "proj-1", "assessment_id": "assessment-1"}

    @patch.object(Neo4jClient, "query")
    def test_delete_project_assessment(self, mock_query):
        client = Neo4jClient()

        client.delete_project_assessment("proj-1", "assessment-1")

        mock_query.assert_called_once()
        query, params = mock_query.call_args[0]
        assert "DETACH DELETE a" in query
        assert params == {"project_id": "proj-1", "assessment_id": "assessment-1"}


class TestNeo4jClientProjectGraph:
    """Tests for project graph helpers."""

    @patch.object(Neo4jClient, "query")
    def test_connect_project_to_nodes_groups_labels(self, mock_query):
        client = Neo4jClient()

        nodes = [
            {"label": "Skill", "name": "Python"},
            {"label": "Skill", "name": "Python"},
            {"label": "Concept", "name": "Closures"},
            {"label": "Topic", "name": "Functional Programming"},
            {"label": "Tool", "name": "Ignored"},
        ]

        client.connect_project_to_nodes("proj-1", nodes)

        assert mock_query.call_count == 3

    @patch.object(Neo4jClient, "query")
    def test_get_projects_for_node(self, mock_query):
        client = Neo4jClient()
        mock_query.return_value = [{"id": "proj-1", "is_default": False}]

        result = client.get_projects_for_node("node-1", "Node Name")

        assert result == [{"id": "proj-1", "is_default": False}]
        mock_query.assert_called_once()
