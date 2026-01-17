"""Neo4j database client with CRUD operations."""

from typing import Any, Dict, List, Optional, Union
from neo4j import GraphDatabase, Driver, Session, Record
from neo4j.exceptions import Neo4jError as Neo4jDriverError

from .exceptions import DatabaseError, ConnectionError, QueryError


class DatabaseClient:
    """Client for interacting with Neo4j database."""
    
    def __init__(self, uri: str, username: str = "neo4j", password: str = "") -> None:
        self.uri = uri
        self.username = username
        self.password = password
        self.driver: Optional[Driver] = None
    
    def connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
        except Neo4jDriverError as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
    
    def disconnect(self) -> None:
        """Close database connection."""
        if self.driver:
            self.driver.close()
            self.driver = None
    
    def _ensure_connected(self) -> None:
        """Ensure database connection is established."""
        if not self.driver:
            raise ConnectionError("Database not connected. Call connect() first.")
    
    def query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Record]:
        """Execute a Cypher query and return results."""
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return list(result)
        except Neo4jDriverError as e:
            raise QueryError(f"Query failed: {e}")
    
    def add_node(
        self,
        label: str,
        properties: Optional[Dict[str, Any]] = None,
        merge: bool = False
    ) -> Dict[str, Any]:
        """Add a node to the database."""
        self._ensure_connected()
        
        properties = properties or {}
        prop_string = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        
        if merge:
            query = f"MERGE (n:{label} {{{prop_string}}}) RETURN n"
        else:
            query = f"CREATE (n:{label} {{{prop_string}}}) RETURN n"
        
        try:
            with self.driver.session() as session:
                result = session.run(query, properties)
                node = result.single()["n"]
                return {
                    "id": node.element_id,
                    "labels": list(node.labels),
                    "properties": dict(node)
                }
        except Neo4jDriverError as e:
            raise QueryError(f"Failed to add node: {e}")
    
    def add_relationship(
        self,
        from_label: str,
        from_properties: Dict[str, Any],
        relationship_type: str,
        to_label: str,
        to_properties: Dict[str, Any],
        relationship_properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a relationship between two nodes."""
        self._ensure_connected()
        
        relationship_properties = relationship_properties or {}
        
        from_props = ", ".join([f"{k}: ${f'from_{k}'}" for k in from_properties.keys()])
        to_props = ", ".join([f"{k}: ${f'to_{k}'}" for k in to_properties.keys()])
        rel_props = ", ".join([f"{k}: ${f'rel_{k}'}" for k in relationship_properties.keys()])
        
        query = f"""
        MATCH (a:{from_label} {{{from_props}}})
        MATCH (b:{to_label} {{{to_props}}})
        CREATE (a)-[r:{relationship_type} {{{rel_props}}}]->(b)
        RETURN r
        """
        
        parameters = {}
        for k, v in from_properties.items():
            parameters[f"from_{k}"] = v
        for k, v in to_properties.items():
            parameters[f"to_{k}"] = v
        for k, v in relationship_properties.items():
            parameters[f"rel_{k}"] = v
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                relationship = result.single()["r"]
                return {
                    "id": relationship.element_id,
                    "type": relationship.type,
                    "properties": dict(relationship),
                    "start_node": relationship.start_node.element_id,
                    "end_node": relationship.end_node.element_id
                }
        except Neo4jDriverError as e:
            raise QueryError(f"Failed to add relationship: {e}")
    
    def search_nodes(
        self,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for nodes matching criteria."""
        self._ensure_connected()
        
        where_clauses = []
        parameters = {}
        
        if label:
            where_clauses.append("n:" + label)
        
        if properties:
            for k, v in properties.items():
                where_clauses.append(f"n.{k} = ${k}")
                parameters[k] = v
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"MATCH (n) WHERE {where_clause} RETURN n {limit_clause}"
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                return [
                    {
                        "id": record["n"].element_id,
                        "labels": list(record["n"].labels),
                        "properties": dict(record["n"])
                    }
                    for record in result
                ]
        except Neo4jDriverError as e:
            raise QueryError(f"Failed to search nodes: {e}")
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by its internal ID."""
        self._ensure_connected()
        
        query = "MATCH (n) WHERE elementId(n) = $id RETURN n"
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {"id": node_id})
                record = result.single()
                if record:
                    node = record["n"]
                    return {
                        "id": node.element_id,
                        "labels": list(node.labels),
                        "properties": dict(node)
                    }
                return None
        except Neo4jDriverError as e:
            raise QueryError(f"Failed to get node: {e}")
    
    def update_node(
        self,
        node_id: str,
        properties: Dict[str, Any],
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update a node's properties and labels."""
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                # First, get the node
                get_query = "MATCH (n) WHERE elementId(n) = $id RETURN n"
                result = session.run(get_query, {"id": node_id})
                node = result.single()["n"]
                
                # Update properties
                if properties:
                    set_clauses = []
                    parameters = {"id": node_id}
                    
                    for k, v in properties.items():
                        set_clauses.append(f"n.{k} = ${k}")
                        parameters[k] = v
                    
                    set_clause = ", ".join(set_clauses)
                    query = f"MATCH (n) WHERE elementId(n) = $id SET {set_clause} RETURN n"
                    result = session.run(query, parameters)
                    node = result.single()["n"]
                
                # Handle labels separately
                if add_labels or remove_labels:
                    current_labels = set(node.labels)
                    
                    # Remove labels first
                    if remove_labels:
                        for label in remove_labels:
                            if label in current_labels:
                                remove_query = f"MATCH (n) WHERE elementId(n) = $id REMOVE n:{label}"
                                session.run(remove_query, {"id": node_id})
                                current_labels.discard(label)
                    
                    # Add labels
                    if add_labels:
                        for label in add_labels:
                            if label not in current_labels:
                                add_query = f"MATCH (n) WHERE elementId(n) = $id SET n:{label}"
                                session.run(add_query, {"id": node_id})
                                current_labels.add(label)
                    
                    # Refresh node to get updated state
                    refresh_query = "MATCH (n) WHERE elementId(n) = $id RETURN n"
                    result = session.run(refresh_query, {"id": node_id})
                    node = result.single()["n"]
                
                return {
                    "id": node.element_id,
                    "labels": list(node.labels),
                    "properties": dict(node)
                }
        except Neo4jDriverError as e:
            raise QueryError(f"Failed to update node: {e}")
    
    def delete_node(self, node_id: str, detach: bool = True) -> bool:
        """Delete a node from the database."""
        self._ensure_connected()
        
        detach_clause = "DETACH " if detach else ""
        query = f"MATCH (n) WHERE elementId(n) = $id {detach_clause}DELETE n"
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {"id": node_id})
                return result.consume().counters.nodes_deleted > 0
        except Neo4jDriverError as e:
            raise QueryError(f"Failed to delete node: {e}")
    
    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship from the database."""
        self._ensure_connected()
        
        query = "MATCH ()-[r]-() WHERE elementId(r) = $id DELETE r"
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {"id": relationship_id})
                return result.consume().counters.relationships_deleted > 0
        except Neo4jDriverError as e:
            raise QueryError(f"Failed to delete relationship: {e}")
    
    def get_relationships(
        self,
        node_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        direction: str = "both"  # "in", "out", "both"
    ) -> List[Dict[str, Any]]:
        """Get relationships from the database."""
        self._ensure_connected()
        
        if direction not in ["in", "out", "both"]:
            raise ValueError("Direction must be 'in', 'out', or 'both'")
        
        where_clauses = []
        parameters = {}
        
        if node_id:
            where_clauses.append("elementId(n) = $node_id")
            parameters["node_id"] = node_id
        
        if relationship_type:
            where_clauses.append("type(r) = $rel_type")
            parameters["rel_type"] = relationship_type
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        if direction == "out":
            match_clause = "MATCH (n)-[r]->(m)"
        elif direction == "in":
            match_clause = "MATCH (n)<-[r]-(m)"
        else:
            match_clause = "MATCH (n)-[r]-(m)"
        
        query = f"{match_clause} WHERE {where_clause} RETURN r, n, m"
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                return [
                    {
                        "id": record["r"].element_id,
                        "type": record["r"].type,
                        "properties": dict(record["r"]),
                        "start_node": record["n"].element_id,
                        "end_node": record["m"].element_id
                    }
                    for record in result
                ]
        except Neo4jDriverError as e:
            raise QueryError(f"Failed to get relationships: {e}")
    
    def __enter__(self) -> "DatabaseClient":
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()