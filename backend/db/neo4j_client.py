"""
Neo4j database client for Endstate.
Provides connection management and graph operations.
"""
import json
import re
from typing import Optional, Any

DEFAULT_PROJECT_ID = "project-all"
DEFAULT_PROJECT_NAME = "All"

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
        properties = node.get("properties")
        if isinstance(properties, dict):
            return {
                "id": node.get("id") or node.get("element_id"),
                "labels": node.get("labels", []),
                "properties": _serialize_neo4j_value(properties),
            }
        return {
            "id": node.get("id") or node.get("element_id"),
            "labels": node.get("labels", []),
            "properties": _serialize_neo4j_value({k: v for k, v in node.items() if k not in ("id", "labels")}),
        }
    node_id = None
    try:
        node_id = node.get("id")
    except Exception:
        node_id = None
    return {
        "id": node_id or (node.element_id if hasattr(node, "element_id") else None),
        "labels": list(node.labels),
        "properties": _serialize_neo4j_value(dict(node)),
    }


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
    return slug or "node"


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
        for label in ("Skill", "Concept", "Topic"):
            try:
                self.merge_nodes_simple(label, match_property="name")
            except Exception:
                continue
    
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
            WHERE prop IS NOT NULL AND SIZE(nodes) > 1
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
        Merge nodes without APOC while preserving relationships.
        
        Args:
            label: Node label to merge
            match_property: Property to match on
            
        Returns:
            Number of duplicate nodes deleted
        """
        duplicates = self.query(f"""
            MATCH (n:{label})
            WITH n.{match_property} AS prop, COLLECT(n) AS nodes
            WHERE prop IS NOT NULL AND SIZE(nodes) > 1
            RETURN elementId(HEAD(nodes)) as keep_id,
                   [node IN TAIL(nodes) | elementId(node)] as dup_ids
        """)

        if not duplicates:
            return 0

        merged_count = 0
        for row in duplicates:
            keep_id = row.get("keep_id")
            dup_ids = row.get("dup_ids") or []
            for dup_id in dup_ids:
                outgoing = self.query(
                    """
                    MATCH (dup)
                    WHERE elementId(dup) = $dup_id
                    MATCH (dup)-[r]->(m)
                    RETURN type(r) as rel_type, properties(r) as props, elementId(m) as target_id
                    """,
                    {"dup_id": dup_id},
                )
                for rel in outgoing:
                    rel_type = rel.get("rel_type", "")
                    if not re.match(r"^[A-Z0-9_]+$", rel_type):
                        continue
                    self.query(
                        f"""
                        MATCH (a) WHERE elementId(a) = $from_id
                        MATCH (b) WHERE elementId(b) = $to_id
                        CREATE (a)-[r:{rel_type}]->(b)
                        SET r += $props
                        """,
                        {"from_id": keep_id, "to_id": rel.get("target_id"), "props": rel.get("props") or {}},
                    )

                incoming = self.query(
                    """
                    MATCH (dup)
                    WHERE elementId(dup) = $dup_id
                    MATCH (m)-[r]->(dup)
                    RETURN type(r) as rel_type, properties(r) as props, elementId(m) as source_id
                    """,
                    {"dup_id": dup_id},
                )
                for rel in incoming:
                    rel_type = rel.get("rel_type", "")
                    if not re.match(r"^[A-Z0-9_]+$", rel_type):
                        continue
                    self.query(
                        f"""
                        MATCH (a) WHERE elementId(a) = $from_id
                        MATCH (b) WHERE elementId(b) = $to_id
                        CREATE (a)-[r:{rel_type}]->(b)
                        SET r += $props
                        """,
                        {"from_id": rel.get("source_id"), "to_id": keep_id, "props": rel.get("props") or {}},
                    )

                self.query(
                    """
                    MATCH (dup)
                    WHERE elementId(dup) = $dup_id
                    DETACH DELETE dup
                    """,
                    {"dup_id": dup_id},
                )
                merged_count += 1

        return merged_count
    
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
        allowed_labels = ["Skill", "Concept", "Topic", "Project", "Milestone"]
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
        rel_stats = self.query(
            """
            CALL db.relationshipTypes() YIELD relationshipType
            CALL {
                WITH relationshipType
                MATCH (n)-[r]->(m)
                WHERE type(r) = relationshipType
                  AND any(label IN labels(n) WHERE label IN $labels)
                  AND any(label IN labels(m) WHERE label IN $labels)
                  AND NOT (n:Project AND COALESCE(n.is_default, false))
                  AND NOT (m:Project AND COALESCE(m.is_default, false))
                RETURN count(r) as count
            }
            RETURN relationshipType, count
            """,
            {"labels": allowed_labels},
        )
        
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
        allowed_labels = ["Skill", "Concept", "Topic", "Project", "Milestone"]
        project_result = self.query(
            """
            MATCH (n:Project)
            WHERE NOT COALESCE(n.is_default, false)
            RETURN labels(n) as labels,
                   properties(n) as properties,
                   elementId(n) as element_id,
                   n.id as id
            """,
        )
        remaining_limit = max(limit - len(project_result), 0)
        other_result = self.query(
            """
            MATCH (n)
            WHERE any(label IN labels(n) WHERE label IN $labels)
              AND NOT (n:Project AND COALESCE(n.is_default, false))
            RETURN labels(n) as labels,
                   properties(n) as properties,
                   elementId(n) as element_id,
                   n.id as id
            LIMIT $limit
            """,
            {"limit": remaining_limit, "labels": allowed_labels},
        )
        combined = project_result + other_result
        seen = set()
        nodes = []
        for row in combined:
            node = _serialize_node(row)
            node_id = node.get("id")
            if node_id in seen:
                continue
            seen.add(node_id)
            nodes.append(node)
        return nodes

    def get_knowledge_graph_relationships(self, limit: int = 100) -> list[dict]:
        """
        Get relationships for the knowledge graph (excluding chat relationships).

        Args:
            limit: Maximum number of relationships to return

        Returns:
            List of relationship dictionaries
        """
        allowed_labels = ["Skill", "Concept", "Topic", "Project", "Milestone"]
        query = """
            MATCH (n)-[r]->(m)
            WHERE any(label IN labels(n) WHERE label IN $labels)
              AND any(label IN labels(m) WHERE label IN $labels)
              AND NOT (n:Project AND COALESCE(n.is_default, false))
              AND NOT (m:Project AND COALESCE(m.is_default, false))
            RETURN COALESCE(n.id, elementId(n)) as source,
                   type(r) as type,
                   COALESCE(m.id, elementId(m)) as target,
                   properties(r) as properties
            LIMIT $limit
        """
        result = self.query(query, {"limit": limit, "labels": allowed_labels})
        return result

    def get_knowledge_graph_stats(self) -> dict:
        """
        Get statistics for the knowledge graph (excluding chat nodes).

        Returns:
            Dictionary with node counts by label and relationship counts by type
        """
        allowed_labels = ["Skill", "Concept", "Topic", "Project", "Milestone"]
        node_stats = self.query(
            """
            UNWIND $labels as label
            CALL {
                WITH label
                MATCH (n)
                WHERE label IN labels(n)
                  AND NOT (n:Project AND COALESCE(n.is_default, false))
                RETURN count(n) as count
            }
            RETURN label, count
            """,
            {"labels": allowed_labels},
        )

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
        allowed_labels = ["Skill", "Concept", "Topic", "Project", "Milestone"]
        result = self.query(
            """
            MATCH (n)
            WHERE any(label IN labels(n) WHERE label IN $labels)
              AND NOT (n:Project AND COALESCE(n.is_default, false))
            RETURN count(n) as count
            """,
            {"labels": allowed_labels},
        )
        return result[0]["count"] if result else 0

    def get_knowledge_graph_relationship_count(self) -> int:
        """Get count of knowledge graph relationships (excluding chat relationships)."""
        allowed_labels = ["Skill", "Concept", "Topic", "Project"]
        result = self.query(
            """
            MATCH (n)-[r]->(m)
            WHERE any(label IN labels(n) WHERE label IN $labels)
              AND any(label IN labels(m) WHERE label IN $labels)
              AND NOT (n:Project AND COALESCE(n.is_default, false))
              AND NOT (m:Project AND COALESCE(m.is_default, false))
            RETURN count(r) as count
            """,
            {"labels": allowed_labels},
        )
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

    def get_chat_session_metadata(self, session_id: str) -> dict:
        """Get chat session metadata."""
        result = self.query(
            """
            MATCH (s:ChatSession {id: $session_id})
            RETURN s.last_project_id as last_project_id,
                   s.last_proposal_hash as last_proposal_hash
            """,
            {"session_id": session_id},
        )
        return result[0] if result else {}

    def update_chat_session_metadata(self, session_id: str, project_id: str, proposal_hash: str | None) -> None:
        """Update chat session metadata after project creation."""
        self.query(
            """
            MATCH (s:ChatSession {id: $session_id})
            SET s.last_project_id = $project_id,
                s.last_proposal_hash = $proposal_hash,
                s.updated_at = datetime()
            """,
            {"session_id": session_id, "project_id": project_id, "proposal_hash": proposal_hash},
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

    def upsert_project_summary(
        self,
        project_id: str,
        project_name: str,
        summary_json: str,
        is_default: bool = False,
    ) -> None:
        """Create or update a project summary and its KG project node."""
        self.query(
            """
            MERGE (ps:ProjectSummary {id: $project_id})
            ON CREATE SET ps.created_at = datetime()
            SET ps.project_name = $project_name,
                ps.summary_json = $summary_json,
                ps.updated_at = datetime(),
                ps.is_default = $is_default
            MERGE (p:Project {id: $project_id})
            ON CREATE SET p.created_at = datetime()
            SET p.name = $project_name,
                p.is_default = $is_default,
                p.updated_at = datetime()
            MERGE (ps)-[:SUMMARY_FOR]->(p)
            """,
            {
                "project_id": project_id,
                "project_name": project_name,
                "summary_json": summary_json,
                "is_default": is_default,
            },
        )

    def rename_project_summary(self, project_id: str, project_name: str, summary_json: str) -> None:
        """Rename an existing project summary and its KG project node."""
        self.query(
            """
            MATCH (ps:ProjectSummary {id: $project_id})
            SET ps.project_name = $project_name,
                ps.summary_json = $summary_json,
                ps.updated_at = datetime()
            WITH ps
            MATCH (p:Project {id: $project_id})
            SET p.name = $project_name,
                p.updated_at = datetime()
            """,
            {
                "project_id": project_id,
                "project_name": project_name,
                "summary_json": summary_json,
            },
        )

    def update_project_summary_json(self, project_id: str, summary_json: str) -> None:
        """Update project summary JSON payload."""
        self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})
            SET p.summary_json = $summary_json,
                p.updated_at = datetime()
            """,
            {
                "project_id": project_id,
                "summary_json": summary_json,
            },
        )

    def ensure_default_project(self) -> None:
        """Ensure the default 'All' project exists."""
        summary_json = json.dumps({
            "agreed_project": {
                "name": DEFAULT_PROJECT_NAME,
                "description": "Default collection for unassigned lessons and assessments.",
                "timeline": "",
                "milestones": [],
            },
            "user_profile": {
                "interests": [],
                "skill_level": "intermediate",
                "time_available": "2 hours/week",
                "learning_style": "hybrid",
            },
            "is_default": True,
        })
        self.upsert_project_summary(DEFAULT_PROJECT_ID, DEFAULT_PROJECT_NAME, summary_json, is_default=True)

    def ensure_project_nodes(self) -> None:
        """Ensure every project summary has a KG project node."""
        self.query(
            """
            MATCH (ps:ProjectSummary)
            MERGE (p:Project {id: ps.id})
            ON CREATE SET p.created_at = datetime()
            SET p.name = ps.project_name,
                p.updated_at = datetime(),
                p.is_default = COALESCE(ps.is_default, false)
            MERGE (ps)-[:SUMMARY_FOR]->(p)
            """
        )

    def upsert_project_profile_node(self, project_id: str, profile: dict) -> None:
        """Create or update a project profile node and link to project."""
        profile_id = f"profile-{project_id}"
        self.query(
            """
            MATCH (p:Project {id: $project_id})
            MERGE (u:UserProfile {id: $profile_id})
            ON CREATE SET u.created_at = datetime()
            SET u.interests = $interests,
                u.skill_level = $skill_level,
                u.time_available = $time_available,
                u.learning_style = $learning_style,
                u.updated_at = datetime()
            MERGE (p)-[:HAS_PROFILE]->(u)
            """,
            {
                "project_id": project_id,
                "profile_id": profile_id,
                "interests": profile.get("interests", []),
                "skill_level": profile.get("skill_level"),
                "time_available": profile.get("time_available"),
                "learning_style": profile.get("learning_style"),
            },
        )

    def upsert_project_nodes_from_summary(self, project_id: str, summary: dict) -> dict:
        """Create KG nodes from project summary fields and link to the project."""
        nodes: dict[str, set[str]] = {
            "Skill": set(),
            "Concept": set(),
            "Topic": set(),
            "Milestone": set(),
        }
        for key, label in (("skills", "Skill"), ("concepts", "Concept"), ("topics", "Topic")):
            values = summary.get(key) if isinstance(summary.get(key), list) else []
            for value in values:
                if isinstance(value, str) and value.strip():
                    nodes[label].add(value.strip())
        agreed = summary.get("agreed_project", {}) if isinstance(summary.get("agreed_project"), dict) else {}
        milestones = agreed.get("milestones") if isinstance(agreed.get("milestones"), list) else []
        for value in milestones:
            if isinstance(value, str) and value.strip():
                nodes["Milestone"].add(value.strip())

        relationship_count = 0
        for label, names in nodes.items():
            if not names:
                continue
            payload = [{"name": name, "id": f"{label.lower()}-{_slugify(name)}"} for name in names]
            rel_type = {
                "Skill": "HAS_SKILL",
                "Concept": "HAS_CONCEPT",
                "Topic": "HAS_TOPIC",
                "Milestone": "HAS_MILESTONE",
            }.get(label, "HAS_NODE")
            self.query(
                f"""
                MATCH (p:Project {{id: $project_id}})
                UNWIND $items as item
                MERGE (n:{label} {{name: item.name}})
                ON CREATE SET n.created_at = datetime()
                SET n.name = item.name,
                    n.id = COALESCE(n.id, item.id),
                    n.updated_at = datetime()
                MERGE (p)-[:HAS_NODE]->(n)
                MERGE (p)-[:{rel_type}]->(n)
                """,
                {"project_id": project_id, "items": payload},
            )
            if label == "Milestone":
                self.query(
                    """
                    MATCH (p:Project {id: $project_id})
                    UNWIND $items as item
                    MATCH (m:Milestone {name: item.name})
                    MERGE (m)-[:PART_OF]->(p)
                    """,
                    {"project_id": project_id, "items": payload},
                )
                relationship_count += len(payload) * 3
            else:
                relationship_count += len(payload) * 2

        milestone_skill_pairs: list[dict] = []
        if nodes["Milestone"] and nodes["Skill"]:
            for milestone in nodes["Milestone"]:
                for skill in nodes["Skill"]:
                    if skill.lower() in milestone.lower():
                        milestone_skill_pairs.append({"milestone": milestone, "skill": skill})
        if milestone_skill_pairs:
            self.query(
                """
                UNWIND $pairs as pair
                MATCH (m:Milestone {name: pair.milestone})
                MATCH (s:Skill {name: pair.skill})
                MERGE (m)-[:REQUIRES]->(s)
                """,
                {"pairs": milestone_skill_pairs},
            )
            relationship_count += len(milestone_skill_pairs)

        for label in ("Skill", "Concept", "Topic"):
            try:
                self.merge_nodes_simple(label, match_property="name")
            except Exception:
                continue
        return {"nodes": sum(len(names) for names in nodes.values()), "relationships": relationship_count}

    def connect_project_to_nodes(self, project_id: str, nodes: list[dict]) -> None:
        """Connect a project to skill/concept/topic nodes by name."""
        grouped: dict[str, set[str]] = {}
        for node in nodes:
            name = node.get("name")
            label = node.get("label")
            if not name or label not in {"Skill", "Concept", "Topic", "Milestone"}:
                continue
            grouped.setdefault(label, set()).add(name)

        for label, names in grouped.items():
            rel_type = {
                "Skill": "HAS_SKILL",
                "Concept": "HAS_CONCEPT",
                "Topic": "HAS_TOPIC",
                "Milestone": "HAS_MILESTONE",
            }.get(label, "HAS_NODE")
            self.query(
                f"""
                MATCH (p:Project {{id: $project_id}})
                UNWIND $names as node_name
                MATCH (n:{label} {{name: node_name}})
                MERGE (p)-[:HAS_NODE]->(n)
                MERGE (p)-[:{rel_type}]->(n)
                """,
                {"project_id": project_id, "names": list(names)},
            )

    def list_project_nodes(self, project_id: str) -> list[dict]:
        """List KG nodes connected to a project."""
        result = self.query(
            """
            MATCH (p:Project {id: $project_id})-[:HAS_NODE]->(n)
            RETURN n
            ORDER BY n.name ASC
            """,
            {"project_id": project_id},
        )
        return [_serialize_node(row["n"]) for row in result]

    def clear_project_nodes(self, project_id: str) -> None:
        """Remove project links and delete nodes unique to this project."""
        self.query(
            """
            MATCH (p:Project {id: $project_id})-[rel:HAS_NODE]->(n)
            WHERE NOT EXISTS {
                MATCH (p2:Project)-[:HAS_NODE]->(n)
                WHERE p2.id <> $project_id
            }
            DETACH DELETE n
            """,
            {"project_id": project_id},
        )
        self.query(
            """
            MATCH (p:Project {id: $project_id})-[rel:HAS_NODE]->(n)
            DELETE rel
            """,
            {"project_id": project_id},
        )

    def get_projects_for_node(self, node_id: str, node_name: str) -> list[dict]:
        """Get projects connected to a node by id or name."""
        result = self.query(
            """
            MATCH (p:Project)-[:HAS_NODE]->(n)
            WHERE n.id = $node_id OR elementId(n) = $node_id OR n.name = $node_name
            RETURN p.id as id, p.is_default as is_default
            ORDER BY p.created_at ASC
            """,
            {"node_id": node_id, "node_name": node_name},
        )
        return result

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
            MATCH (ps:ProjectSummary {id: $project_id})
            OPTIONAL MATCH (ps)-[:HAS_PROJECT_MESSAGE]->(m:ProjectMessage)
            OPTIONAL MATCH (ps)-[:HAS_LESSON]->(l:ProjectLesson)
            OPTIONAL MATCH (ps)-[:HAS_ASSESSMENT]->(a:ProjectAssessment)
            OPTIONAL MATCH (ps)-[:SUMMARY_FOR]->(p:Project)
            OPTIONAL MATCH (p)-[:HAS_PROFILE]->(u:UserProfile)
            DETACH DELETE ps, m, l, a, u, p
            """,
            {"project_id": project_id},
        )

    def clear_project_content(self, project_id: str) -> None:
        """Clear lessons, assessments, and messages for a project without deleting it."""
        self.query(
            """
            MATCH (ps:ProjectSummary {id: $project_id})
            OPTIONAL MATCH (ps)-[:HAS_PROJECT_MESSAGE]->(m:ProjectMessage)
            OPTIONAL MATCH (ps)-[:HAS_LESSON]->(l:ProjectLesson)
            OPTIONAL MATCH (ps)-[:HAS_ASSESSMENT]->(a:ProjectAssessment)
            DETACH DELETE m, l, a
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

    def save_project_lesson(
        self,
        project_id: str,
        lesson_id: str,
        node_id: str,
        title: str,
        explanation: str,
        task: str,
        lesson_index: int,
    ) -> None:
        """Persist a generated lesson."""
        self.query(
            """
            MATCH (ps:ProjectSummary {id: $project_id})
            MATCH (p:Project {id: $project_id})
            CREATE (l:ProjectLesson {
                id: $lesson_id,
                node_id: $node_id,
                title: $title,
                explanation: $explanation,
                task: $task,
                lesson_index: $lesson_index,
                archived: false,
                created_at: datetime()
            })
            CREATE (ps)-[:HAS_LESSON]->(l)
            CREATE (p)-[:HAS_LESSON]->(l)
            WITH l
            OPTIONAL MATCH (n {id: $node_id})
            FOREACH (_ IN CASE WHEN n IS NULL THEN [] ELSE [1] END |
                MERGE (l)-[:ABOUT]->(n)
            )
            """,
            {
                "project_id": project_id,
                "lesson_id": lesson_id,
                "node_id": node_id,
                "title": title,
                "explanation": explanation,
                "task": task,
                "lesson_index": lesson_index,
            },
        )

    def ensure_lesson_index(self) -> None:
        """Ensure lesson_index exists on all ProjectLesson nodes."""
        self.query(
            """
            MATCH (l:ProjectLesson)
            WHERE l.lesson_index IS NULL
            SET l.lesson_index = 0
            """
        )

    def list_project_lessons(self, project_id: str) -> list[dict]:
        """List lessons for a project."""
        self.ensure_lesson_index()
        result = self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})-[:HAS_LESSON]->(l:ProjectLesson)
            RETURN l.id as id, l.node_id as node_id, l.title as title, l.explanation as explanation, l.task as task, l.lesson_index as lesson_index, l.created_at as created_at, l.archived as archived, l.archived_at as archived_at
            ORDER BY l.created_at DESC
            """,
            {"project_id": project_id},
        )
        return result

    def get_project_lesson_by_node(self, project_id: str, node_id: str) -> list[dict]:
        """Get latest lesson for a node in a project."""
        self.ensure_lesson_index()
        result = self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})-[:HAS_LESSON]->(l:ProjectLesson {node_id: $node_id})
            RETURN l.id as id, l.node_id as node_id, l.title as title, l.explanation as explanation, l.task as task, l.lesson_index as lesson_index, l.created_at as created_at, l.archived as archived, l.archived_at as archived_at
            ORDER BY l.created_at DESC
            LIMIT 1
            """,
            {"project_id": project_id, "node_id": node_id},
        )
        return result

    def list_project_lessons_for_node(self, project_id: str, node_id: str) -> list[dict]:
        """List lessons for a node in a project."""
        self.ensure_lesson_index()
        result = self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})-[:HAS_LESSON]->(l:ProjectLesson {node_id: $node_id})
            RETURN l.id as id,
                   l.title as title,
                   l.explanation as explanation,
                   COALESCE(l.lesson_index, 0) as lesson_index,
                   l.created_at as created_at
            ORDER BY l.created_at ASC
            """,
            {"project_id": project_id, "node_id": node_id},
        )
        return result

    def get_project_graph_counts(self, project_id: str) -> dict:
        """Return counts of nodes and relationships connected to a project."""
        node_result = self.query(
            """
            MATCH (p:Project {id: $project_id})-[:HAS_NODE]->(n)
            RETURN count(DISTINCT n) as node_count
            """,
            {"project_id": project_id},
        )
        rel_result = self.query(
            """
            MATCH (p:Project {id: $project_id})-[r]->()
            RETURN count(r) as rel_count
            """,
            {"project_id": project_id},
        )
        return {
            "nodes": node_result[0].get("node_count", 0) if node_result else 0,
            "relationships": rel_result[0].get("rel_count", 0) if rel_result else 0,
        }

    def archive_project_lesson(self, project_id: str, lesson_id: str) -> None:
        """Archive a lesson."""
        self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})-[:HAS_LESSON]->(l:ProjectLesson {id: $lesson_id})
            SET l.archived = true,
                l.archived_at = datetime()
            """,
            {"project_id": project_id, "lesson_id": lesson_id},
        )

    def delete_project_lesson(self, project_id: str, lesson_id: str) -> None:
        """Delete a lesson from a project."""
        self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})-[:HAS_LESSON]->(l:ProjectLesson {id: $lesson_id})
            DETACH DELETE l
            """,
            {"project_id": project_id, "lesson_id": lesson_id},
        )

    def save_project_assessment(
        self,
        project_id: str,
        assessment_id: str,
        lesson_id: str,
        prompt: str,
    ) -> None:
        """Persist an assessment for a lesson."""
        self.query(
            """
            MATCH (ps:ProjectSummary {id: $project_id})
            MATCH (p:Project {id: $project_id})
            CREATE (a:ProjectAssessment {
                id: $assessment_id,
                lesson_id: $lesson_id,
                prompt: $prompt,
                status: 'pending',
                archived: false,
                created_at: datetime(),
                updated_at: datetime()
            })
            CREATE (ps)-[:HAS_ASSESSMENT]->(a)
            CREATE (p)-[:HAS_ASSESSMENT]->(a)
            WITH a
            MATCH (l:ProjectLesson {id: $lesson_id})
            CREATE (a)-[:ASSESSMENT_FOR]->(l)
            """,
            {
                "project_id": project_id,
                "assessment_id": assessment_id,
                "lesson_id": lesson_id,
                "prompt": prompt,
            },
        )

    def list_project_assessments(self, project_id: str) -> list[dict]:
        """List assessments for a project."""
        result = self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})-[:HAS_ASSESSMENT]->(a:ProjectAssessment)
            RETURN a.id as id, a.lesson_id as lesson_id, a.prompt as prompt, a.status as status, a.feedback as feedback, a.created_at as created_at, a.updated_at as updated_at, a.archived as archived, a.archived_at as archived_at
            ORDER BY a.created_at DESC
            """,
            {"project_id": project_id},
        )
        return result

    def update_project_assessment(
        self,
        assessment_id: str,
        status: str,
        feedback: str,
        answer: str,
        archived: bool | None = None,
    ) -> None:
        """Update assessment evaluation."""
        self.query(
            """
            MATCH (a:ProjectAssessment {id: $assessment_id})
            SET a.status = $status,
                a.feedback = $feedback,
                a.answer = $answer,
                a.archived = CASE WHEN $archived IS NULL THEN a.archived ELSE $archived END,
                a.archived_at = CASE
                    WHEN $archived IS NULL THEN a.archived_at
                    WHEN $archived THEN datetime()
                    ELSE null
                END,
                a.updated_at = datetime()
            """,
            {
                "assessment_id": assessment_id,
                "status": status,
                "feedback": feedback,
                "answer": answer,
                "archived": archived,
            },
        )

    def archive_project_assessment(self, project_id: str, assessment_id: str) -> None:
        """Archive an assessment."""
        self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})-[:HAS_ASSESSMENT]->(a:ProjectAssessment {id: $assessment_id})
            SET a.archived = true,
                a.archived_at = datetime()
            """,
            {"project_id": project_id, "assessment_id": assessment_id},
        )

    def delete_project_assessment(self, project_id: str, assessment_id: str) -> None:
        """Delete an assessment from a project."""
        self.query(
            """
            MATCH (p:ProjectSummary {id: $project_id})-[:HAS_ASSESSMENT]->(a:ProjectAssessment {id: $assessment_id})
            DETACH DELETE a
            """,
            {"project_id": project_id, "assessment_id": assessment_id},
        )

    def get_node_by_id(self, node_id: str) -> Optional[dict]:
        """Get a node by its ID."""
        result = self.query(
            "MATCH (n) WHERE n.id = $node_id OR elementId(n) = $node_id RETURN n",
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
            MATCH (n)-[r]-()
            WHERE n.id = $node_id OR elementId(n) = $node_id
            RETURN COUNT(r) as rel_count
            """,
            {"node_id": node_id}
        )
        rel_count = count_result[0].get("rel_count", 0) if count_result else 0
        
        # Then delete the node with relationships
        self.query(
            """
            MATCH (n)
            WHERE n.id = $node_id OR elementId(n) = $node_id
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
            MATCH (n)-[r]-(connected)
            WHERE n.id = $node_id OR elementId(n) = $node_id
            RETURN COALESCE(connected.id, elementId(connected)) as id, labels(connected) as labels, type(r) as rel_type
            """,
            {"node_id": node_id}
        )
        return result
