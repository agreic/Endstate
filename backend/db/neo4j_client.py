"""
Neo4j database client for Endstate.
Provides connection management and graph operations.
"""
from typing import Optional, Any

from langchain_neo4j import Neo4jGraph
from neo4j import GraphDatabase, Result, RoutingControl
from neo4j.time import DateTime

from ..config import Neo4jConfig, config


def _serialize_neo4j_value(value: Any) -> Any:
    """Serialize Neo4j types to JSON-compatible Python types."""
    if isinstance(value, DateTime):
        return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    elif isinstance(value, list):
        return [_serialize_neo4j_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: _serialize_neo4j_value(v) for k, v in value.items()}
    return value


def _serialize_node(node) -> dict:
    """Serialize a Neo4j Node object to a dictionary."""
    if isinstance(node, dict):
        return {
            "id": node.get("id") or node.get("element_id"),
            "labels": node.get("labels", []),
            "properties": _serialize_neo4j_value({k: v for k, v in node.items() if k not in ("id", "labels")}),
        }
    return {
        "id": node.element_id if hasattr(node, 'element_id') else node.get("id"),
        "labels": list(node.labels),
        "properties": _serialize_neo4j_value(dict(node)),
    }


class Neo4jClient:
    """
    Neo4j database client with graph operations.
    
    Supports both LangChain Neo4jGraph for LLM operations
    and direct Neo4j driver for custom queries.
    """
    
    def __init__(self, neo4j_config: Optional[Neo4jConfig] = None):
        """
        Initialize Neo4j client.
        
        Args:
            neo4j_config: Optional config override. Uses global config if not provided.
        """
        self._config = neo4j_config or config.neo4j
        self._graph: Optional[Neo4jGraph] = None
        self._driver = None
    
    @property
    def graph(self) -> Neo4jGraph:
        """Get or create LangChain Neo4jGraph instance."""
        if self._graph is None:
            self._graph = Neo4jGraph(
                url=self._config.uri,
                username=self._config.username,
                password=self._config.password,
                database=self._config.database,
                refresh_schema=False,
            )
        return self._graph
    
    @property
    def driver(self):
        """Get or create Neo4j driver for direct queries."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._config.uri,
                auth=(self._config.username, self._config.password),
            )
        return self._driver
    
    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection successful, raises exception otherwise.
        """
        try:
            self.graph.query("RETURN 1 as test")
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
    
    def query(self, cypher: str, params: Optional[dict] = None) -> list[dict]:
        """
        Execute a Cypher query.
        
        Args:
            cypher: Cypher query string
            params: Optional query parameters
            
        Returns:
            List of result dictionaries
        """
        return self.graph.query(cypher, params or {})
    
    def clean_graph(self) -> None:
        """Delete all nodes and relationships from the graph."""
        self.query("MATCH (n) DETACH DELETE n")
    
    def clean_by_label(self, label: str) -> int:
        """
        Delete all nodes with a specific label.
        
        Args:
            label: Node label to delete
            
        Returns:
            Number of nodes deleted
        """
        result = self.query(
            f"MATCH (n:{label}) DETACH DELETE n RETURN count(n) as deleted"
        )
        return result[0]["deleted"] if result else 0
    
    def add_graph_documents(
        self,
        documents: list,
        include_source: bool = False,
        base_entity_label: bool = True,
    ) -> None:
        """
        Add graph documents to the database.
        
        Args:
            documents: List of GraphDocument objects from LLM extraction
            include_source: Whether to include source document nodes
            base_entity_label: Whether to add __Entity__ label to all nodes
        """
        self.graph.add_graph_documents(
            documents,
            include_source=include_source,
            baseEntityLabel=base_entity_label,
        )
    
    def merge_nodes(self, label: str, match_property: str = "id") -> int:
        """
        Merge duplicate nodes based on a property.
        
        Args:
            label: Node label to merge
            match_property: Property to match on (default: "id")
            
        Returns:
            Number of nodes merged
        """
        # Find duplicates and merge them
        result = self.query(f"""
            MATCH (n:{label})
            WITH n.{match_property} AS prop, COLLECT(n) AS nodes
            WHERE SIZE(nodes) > 1
            CALL {{
                WITH nodes
                WITH HEAD(nodes) AS keep, TAIL(nodes) AS duplicates
                UNWIND duplicates AS dup
                // Transfer relationships
                CALL {{
                    WITH keep, dup
                    MATCH (dup)-[r]->()
                    WITH keep, dup, COLLECT(r) as rels
                    UNWIND rels as r
                    WITH keep, dup, r, STARTNODE(r) as start, ENDNODE(r) as end, TYPE(r) as type
                    CALL apoc.create.relationship(keep, type, PROPERTIES(r), end) YIELD rel
                    RETURN count(*) as created
                }}
                CALL {{
                    WITH keep, dup
                    MATCH ()-[r]->(dup)
                    WITH keep, dup, COLLECT(r) as rels
                    UNWIND rels as r
                    WITH keep, dup, r, STARTNODE(r) as start, ENDNODE(r) as end, TYPE(r) as type
                    CALL apoc.create.relationship(start, type, PROPERTIES(r), keep) YIELD rel
                    RETURN count(*) as created
                }}
                // Delete duplicate
                DETACH DELETE dup
                RETURN count(*) as merged
            }}
            RETURN SUM(merged) as total_merged
        """)
        return result[0]["total_merged"] if result else 0
    
    def merge_nodes_simple(self, label: str, match_property: str = "id") -> int:
        """
        Simple node merge without APOC (for databases without APOC plugin).
        Merges nodes by keeping the first and deleting duplicates.
        Note: This version doesn't transfer relationships from duplicates.
        
        Args:
            label: Node label to merge
            match_property: Property to match on
            
        Returns:
            Number of duplicate nodes deleted
        """
        result = self.query(f"""
            MATCH (n:{label})
            WITH n.{match_property} AS prop, COLLECT(n) AS nodes
            WHERE SIZE(nodes) > 1
            WITH nodes, HEAD(nodes) AS keep
            UNWIND TAIL(nodes) AS dup
            DETACH DELETE dup
            RETURN count(dup) as deleted
        """)
        return result[0]["deleted"] if result else 0
    
    def get_node_count(self, label: Optional[str] = None) -> int:
        """
        Get count of nodes.
        
        Args:
            label: Optional label to filter by
            
        Returns:
            Number of nodes
        """
        if label:
            result = self.query(f"MATCH (n:{label}) RETURN count(n) as count")
        else:
            result = self.query("MATCH (n) RETURN count(n) as count")
        return result[0]["count"] if result else 0
    
    def get_relationship_count(self, rel_type: Optional[str] = None) -> int:
        """
        Get count of relationships.
        
        Args:
            rel_type: Optional relationship type to filter by
            
        Returns:
            Number of relationships
        """
        if rel_type:
            result = self.query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
        else:
            result = self.query("MATCH ()-[r]->() RETURN count(r) as count")
        return result[0]["count"] if result else 0
    
    def get_graph_stats(self) -> dict:
        """
        Get statistics about the current graph.
        
        Returns:
            Dictionary with node counts by label and relationship counts by type
        """
        # Get node labels and counts
        node_stats = self.query("""
            CALL db.labels() YIELD label
            CALL {
                WITH label
                MATCH (n) WHERE label IN labels(n)
                RETURN count(n) as count
            }
            RETURN label, count
        """)
        
        # Get relationship types and counts
        rel_stats = self.query("""
            CALL db.relationshipTypes() YIELD relationshipType
            CALL {
                WITH relationshipType
                MATCH ()-[r]->() WHERE type(r) = relationshipType
                RETURN count(r) as count
            }
            RETURN relationshipType, count
        """)
        
        return {
            "nodes": {row["label"]: row["count"] for row in node_stats},
            "relationships": {row["relationshipType"]: row["count"] for row in rel_stats},
            "total_nodes": self.get_node_count(),
            "total_relationships": self.get_relationship_count(),
        }
    
    def get_all_nodes(self, label: Optional[str] = None, limit: int = 100) -> list[dict]:
        """
        Get all nodes, optionally filtered by label.

        Args:
            label: Optional label to filter by
            limit: Maximum number of nodes to return

        Returns:
            List of node dictionaries with id, labels, and properties
        """
        if label:
            query = f"MATCH (n:{label}) RETURN n LIMIT {limit}"
        else:
            query = f"MATCH (n) RETURN n LIMIT {limit}"

        result = self.query(query)
        return [_serialize_node(row["n"]) for row in result]

    def get_knowledge_graph_nodes(self, limit: int = 100) -> list[dict]:
        """
        Get nodes for the knowledge graph (excluding chat nodes).

        Args:
            limit: Maximum number of nodes to return

        Returns:
            List of node dictionaries
        """
        query = """
            MATCH (n)
            WHERE NOT 'ChatSession' IN labels(n)
              AND NOT 'ChatMessage' IN labels(n)
              AND NOT 'ProjectSummary' IN labels(n)
              AND NOT 'ProjectMessage' IN labels(n)
            RETURN n
            LIMIT $limit
        """
        result = self.query(query, {"limit": limit})
        return [_serialize_node(row["n"]) for row in result]

    def get_knowledge_graph_relationships(self, limit: int = 100) -> list[dict]:
        """
        Get relationships for the knowledge graph (excluding chat relationships).

        Args:
            limit: Maximum number of relationships to return

        Returns:
            List of relationship dictionaries
        """
        query = """
            MATCH (n)-[r]->(m)
            WHERE NOT 'ChatSession' IN labels(n)
              AND NOT 'ChatMessage' IN labels(n)
              AND NOT 'ProjectSummary' IN labels(n)
              AND NOT 'ProjectMessage' IN labels(n)
              AND NOT 'ChatSession' IN labels(m)
              AND NOT 'ChatMessage' IN labels(m)
              AND NOT 'ProjectSummary' IN labels(m)
              AND NOT 'ProjectMessage' IN labels(m)
            RETURN n.id as source, type(r) as type, m.id as target, properties(r) as properties
            LIMIT $limit
        """
        result = self.query(query, {"limit": limit})
        return result

    def get_knowledge_graph_stats(self) -> dict:
        """
        Get statistics for the knowledge graph (excluding chat nodes).

        Returns:
            Dictionary with node counts by label and relationship counts by type
        """
        node_stats = self.query("""
            CALL db.labels() YIELD label
            CALL {
                WITH label
                MATCH (n) WHERE label IN labels(n)
                AND NOT 'ChatSession' IN labels(n)
                AND NOT 'ChatMessage' IN labels(n)
                AND NOT 'ProjectSummary' IN labels(n)
                AND NOT 'ProjectMessage' IN labels(n)
                RETURN count(n) as count
            }
            RETURN label, count
        """)

        rel_stats = self.query("""
            CALL db.relationshipTypes() YIELD relationshipType
            CALL {
                WITH relationshipType
                MATCH ()-[r]->() WHERE type(r) = relationshipType
                RETURN count(r) as count
            }
            RETURN relationshipType, count
        """)

        return {
            "nodes": {row["label"]: row["count"] for row in node_stats if row["count"] > 0},
            "relationships": {row["relationshipType"]: row["count"] for row in rel_stats if row["count"] > 0},
            "total_nodes": self.get_knowledge_graph_node_count(),
            "total_relationships": self.get_knowledge_graph_relationship_count(),
        }

    def get_knowledge_graph_node_count(self) -> int:
        """Get count of knowledge graph nodes (excluding chat nodes)."""
        result = self.query("""
            MATCH (n)
            WHERE NOT 'ChatSession' IN labels(n)
              AND NOT 'ChatMessage' IN labels(n)
              AND NOT 'ProjectSummary' IN labels(n)
              AND NOT 'ProjectMessage' IN labels(n)
            RETURN count(n) as count
        """)
        return result[0]["count"] if result else 0

    def get_knowledge_graph_relationship_count(self) -> int:
        """Get count of knowledge graph relationships (excluding chat relationships)."""
        result = self.query("""
            MATCH (n)-[r]->(m)
            WHERE NOT 'ChatSession' IN labels(n)
              AND NOT 'ChatMessage' IN labels(n)
              AND NOT 'ProjectSummary' IN labels(n)
              AND NOT 'ProjectMessage' IN labels(n)
              AND NOT 'ChatSession' IN labels(m)
              AND NOT 'ChatMessage' IN labels(m)
              AND NOT 'ProjectSummary' IN labels(m)
              AND NOT 'ProjectMessage' IN labels(m)
            RETURN count(r) as count
        """)
        return result[0]["count"] if result else 0

    def get_all_relationships(self, limit: int = 100) -> list[dict]:
        """
        Get all relationships.
        
        Args:
            limit: Maximum number of relationships to return
            
        Returns:
            List of relationship dictionaries
        """
        result = self.query(f"""
            MATCH (n)-[r]->(m) 
            RETURN n.id as source, type(r) as type, m.id as target, properties(r) as properties
            LIMIT {limit}
        """)
        return result
    
    def visualize_graph(self):
        """
        Get graph data for visualization.
        
        Returns:
            neo4j_viz VisualizationGraph object (requires neo4j-viz package)
        """
        try:
            from neo4j_viz.neo4j import from_neo4j
            
            with self.driver as driver:
                driver.verify_connectivity()
                result = driver.execute_query(
                    "MATCH (n)-[r]->(m) RETURN n,r,m",
                    database_=self._config.database,
                    routing_=RoutingControl.READ,
                    result_transformer_=Result.graph,
                )
            
            return from_neo4j(result)
        except ImportError:
            raise ImportError("neo4j-viz package required for visualization. Install with: pip install neo4j-viz")
    
    def close(self) -> None:
        """Close all connections."""
        if self._driver:
            self._driver.close()
            self._driver = None
        self._graph = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # Don't close - let connection pool manage lifecycle

    def create_chat_session(self, session_id: str) -> None:
        """Create a new chat session node."""
        self.query(
            "MERGE (s:ChatSession {id: $session_id}) SET s.created_at = datetime()",
            {"session_id": session_id}
        )

    def add_chat_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to a chat session."""
        self.query(
            """
            MATCH (s:ChatSession {id: $session_id})
            CREATE (m:ChatMessage {role: $role, content: $content, timestamp: datetime()})
            CREATE (s)-[:HAS_MESSAGE]->(m)
            """,
            {"session_id": session_id, "role": role, "content": content}
        )

    def get_chat_history(self, session_id: str) -> list[dict]:
        """Get chat history for a session."""
        result = self.query(
            """
            MATCH (s:ChatSession {id: $session_id})-[:HAS_MESSAGE]->(m:ChatMessage)
            RETURN m.role as role, m.content as content, m.timestamp as timestamp
            ORDER BY m.timestamp
            """,
            {"session_id": session_id}
        )
        messages = []
        for row in result:
            timestamp = row.get("timestamp")
            if isinstance(timestamp, DateTime):
                timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            messages.append({
                "role": row.get("role"),
                "content": row.get("content"),
                "timestamp": timestamp,
            })
        return messages

    def get_all_sessions(self) -> list[dict]:
        """Get all chat sessions."""
        result = self.query(
            """
            MATCH (s:ChatSession)
            OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)
            WITH s, count(m) as message_count
            RETURN s.id as id, s.created_at as created_at, message_count
            ORDER BY s.created_at DESC
            """
        )
        sessions = []
        for row in result:
            created_at = row.get("created_at")
            if isinstance(created_at, DateTime):
                created_at = created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            sessions.append({
                "id": row.get("id"),
                "created_at": created_at,
                "message_count": row.get("message_count", 0),
            })
        return sessions

    def delete_chat_session(self, session_id: str) -> None:
        """Delete a chat session and all its messages."""
        self.query(
            "MATCH (s:ChatSession {id: $session_id}) DETACH DELETE s",
            {"session_id": session_id}
        )

    def set_session_locked(self, session_id: str, locked: bool) -> None:
        """Set the locked state of a chat session."""
        self.query(
            "MATCH (s:ChatSession {id: $session_id}) SET s.is_processing = $locked",
            {"session_id": session_id, "locked": locked}
        )

    def is_session_locked(self, session_id: str) -> bool:
        """Check if a chat session is locked (processing)."""
        result = self.query(
            "MATCH (s:ChatSession {id: $session_id}) RETURN COALESCE(s.is_processing, false) as locked",
            {"session_id": session_id}
        )
        return result[0].get("locked", False) if result else False

    def upsert_project_summary(self, project_id: str, project_name: str, summary_json: str) -> None:
        """Create or update a project summary."""
        self.query(
            """
            MERGE (p:ProjectSummary {id: $project_id})
            ON CREATE SET p.created_at = datetime()
            SET p.project_name = $project_name,
                p.summary_json = $summary_json,
                p.updated_at = datetime()
            """,
            {
                "project_id": project_id,
                "project_name": project_name,
                "summary_json": summary_json,
            },
        )

    def rename_project_summary(self, project_id: str, project_name: str, summary_json: str) -> None:
        """Rename an existing project summary."""
        self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})
            SET p.project_name = $project_name,
                p.summary_json = $summary_json,
                p.updated_at = datetime()
            """,
            {
                "project_id": project_id,
                "project_name": project_name,
                "summary_json": summary_json,
            },
        )

    def list_project_summaries(self, limit: int = 10) -> list[dict]:
        """List recent project summaries."""
        result = self.query(
            """
            MATCH (p:ProjectSummary)
            RETURN p.id as id, p.project_name as name, p.created_at as created_at, p.updated_at as updated_at, p.summary_json as summary_json
            ORDER BY p.created_at DESC
            LIMIT $limit
            """,
            {"limit": limit},
        )
        return result

    def get_project_summary(self, project_id: str) -> list[dict]:
        """Get a project summary by id."""
        result = self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})
            RETURN p.id as id, p.project_name as name, p.created_at as created_at, p.updated_at as updated_at, p.summary_json as summary_json
            """,
            {"project_id": project_id},
        )
        return result

    def delete_project_summary(self, project_id: str) -> None:
        """Delete a project summary and its chat history."""
        self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})
            OPTIONAL MATCH (p)-[:HAS_PROJECT_MESSAGE]->(m:ProjectMessage)
            DETACH DELETE p, m
            """,
            {"project_id": project_id},
        )

    def save_project_chat_history(self, project_id: str, messages: list[dict]) -> None:
        """Save project chat history as a snapshot."""
        self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})
            OPTIONAL MATCH (p)-[:HAS_PROJECT_MESSAGE]->(m:ProjectMessage)
            DETACH DELETE m
            """,
            {"project_id": project_id},
        )
        if not messages:
            return
        self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})
            UNWIND $messages as msg
            CREATE (m:ProjectMessage {
                role: msg.role,
                content: msg.content,
                timestamp: msg.timestamp,
                request_id: msg.request_id,
                idx: msg.idx
            })
            CREATE (p)-[:HAS_PROJECT_MESSAGE]->(m)
            """,
            {
                "project_id": project_id,
                "messages": messages,
            },
        )

    def get_project_chat_history(self, project_id: str) -> list[dict]:
        """Get project chat history."""
        result = self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})-[:HAS_PROJECT_MESSAGE]->(m:ProjectMessage)
            RETURN m.role as role, m.content as content, m.timestamp as timestamp, m.request_id as request_id, m.idx as idx
            ORDER BY m.idx ASC
            """,
            {"project_id": project_id},
        )
        return result

    def get_node_by_id(self, node_id: str) -> Optional[dict]:
        """Get a node by its ID."""
        result = self.query(
            "MATCH (n) WHERE n.id = $node_id RETURN n",
            {"node_id": node_id}
        )
        if result:
            return {"node": result[0]["n"]}
        return None

    def delete_node(self, node_id: str) -> dict:
        """
        Delete a node and all its connected relationships.
        
        Args:
            node_id: The ID of the node to delete
            
        Returns:
            Dictionary with deleted node id and count of deleted relationships
        """
        # First get the count of relationships
        count_result = self.query(
            """
            MATCH (n {id: $node_id})-[r]-()
            RETURN COUNT(r) as rel_count
            """,
            {"node_id": node_id}
        )
        rel_count = count_result[0].get("rel_count", 0) if count_result else 0
        
        # Then delete the node with relationships
        self.query(
            """
            MATCH (n {id: $node_id})
            DETACH DELETE n
            """,
            {"node_id": node_id}
        )
        
        return {
            "deleted_node_id": node_id,
            "relationships_deleted": rel_count
        }

    def delete_relationship(self, source_id: str, target_id: str, rel_type: str) -> dict:
        """
        Delete a specific relationship between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            rel_type: Relationship type
            
        Returns:
            Dictionary with deletion status
        """
        result = self.query(
            """
            MATCH (n {id: $source_id})-[r:`$rel_type`]->(m {id: $target_id})
            DELETE r
            RETURN COUNT(r) as deleted_count
            """,
            {"source_id": source_id, "target_id": target_id, "rel_type": rel_type}
        )
        if result:
            return {
                "deleted": True,
                "source": source_id,
                "target": target_id,
                "relationship_type": rel_type,
                "count": result[0].get("deleted_count", 0)
            }
        return {"deleted": False, "error": "Relationship not found"}

    def get_connected_nodes(self, node_id: str) -> list[dict]:
        """
        Get all nodes connected to a specific node.
        
        Args:
            node_id: The ID of the node
            
        Returns:
            List of connected node info with relationship types
        """
        result = self.query(
            """
            MATCH (n {id: $node_id})-[r]-(connected)
            RETURN connected.id as id, labels(connected) as labels, type(r) as rel_type
            """,
            {"node_id": node_id}
        )
        return result
