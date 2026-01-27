"""
Knowledge Graph Service for Endstate.
High-level service that combines LLM extraction with database operations.
"""
from typing import Optional, Union

from langchain_core.language_models import BaseChatModel

from ..config import config, Config
from ..db.neo4j_client import Neo4jClient
from ..llm.provider import get_llm, LLMProvider
from ..llm.graph_transformer import GraphTransformer
from ..schemas.base import GraphSchema
from ..schemas.skill_graph import SkillGraphSchema


class KnowledgeGraphService:
    """
    High-level service for knowledge graph operations.
    
    Combines LLM-based extraction with Neo4j database operations
    for a complete knowledge graph pipeline.
    
    Example:
        ```python
        # Initialize service
        service = KnowledgeGraphService()
        
        # Or with custom provider
        service = KnowledgeGraphService(llm_provider="ollama")
        
        # Extract and add to graph
        await service.extract_and_add("Python is a programming language...")
        
        # Get graph statistics
        stats = service.get_stats()
        
        # Clean up
        service.clean()
        ```
    """
    
    def __init__(
        self,
        llm_provider: Optional[Union[str, LLMProvider]] = None,
        llm: Optional[BaseChatModel] = None,
        schema: Optional[GraphSchema] = None,
        app_config: Optional[Config] = None,
        ignore_tool_usage: bool = False,
    ):
        """
        Initialize KnowledgeGraphService.
        
        Args:
            llm_provider: LLM provider to use ("ollama" or "gemini").
                         Uses config default if not specified.
            llm: Optional pre-configured LLM instance.
            schema: Graph schema for extraction. Defaults to SkillGraphSchema.
            app_config: Optional config override.
            ignore_tool_usage: If True, use prompt-based extraction.
        """
        self._config = app_config or config
        
        # Initialize LLM
        if llm is not None:
            self._llm = llm
        else:
            self._llm = get_llm(provider=llm_provider, llm_config=self._config.llm)
        
        # Initialize components
        self._db = Neo4jClient(self._config.neo4j)
        self._transformer = GraphTransformer(
            llm=self._llm,
            schema=schema or SkillGraphSchema,
            ignore_tool_usage=ignore_tool_usage,
        )
    
    @property
    def db(self) -> Neo4jClient:
        """Get database client."""
        return self._db
    
    @property
    def transformer(self) -> GraphTransformer:
        """Get graph transformer."""
        return self._transformer
    
    @property
    def schema(self) -> GraphSchema:
        """Get current schema."""
        return self._transformer.schema
    
    @schema.setter
    def schema(self, value: GraphSchema) -> None:
        """Set schema."""
        self._transformer.schema = value
    
    # ==================== Connection & Health ====================
    
    def test_connection(self) -> dict:
        """
        Test all connections (database and LLM).
        
        Returns:
            Dictionary with connection status for each component.
        """
        results = {"database": False, "llm": False, "database_error": None, "llm_error": None}
        
        # Test database
        try:
            self._db.test_connection()
            results["database"] = True
        except Exception as e:
            results["database_error"] = str(e)
        
        # Test LLM
        try:
            from ..llm.provider import test_llm
            success, message = test_llm(self._llm)
            results["llm"] = success
            if not success:
                results["llm_error"] = message
        except Exception as e:
            results["llm_error"] = str(e)
        
        return results
    
    # ==================== Extraction Operations ====================
    
    def extract(self, text: str) -> list:
        """
        Extract graph documents from text without adding to database.
        
        Args:
            text: Text to extract entities and relationships from.
            
        Returns:
            List of GraphDocument objects.
        """
        return self._transformer.process_text(text)
    
    async def aextract(self, text: str, fallback_on_empty: bool = True) -> list:
        """
        Extract graph documents from text asynchronously.
        
        Args:
            text: Text to extract from.
            fallback_on_empty: If True, try a simpler extraction if primary fails.
            
        Returns:
            List of GraphDocument objects.
        """
        try:
            docs = await self._transformer.aprocess_text(text)
            # # If primary extraction returned nothing, try a fallback with a simpler prompt
            # if fallback_on_empty and (not docs or not docs[0].nodes):
            #     provider = self._config.llm.provider
            #     if provider in ("openrouter", "ollama"):
            #         print(f"[KnowledgeGraph] Primary extraction returned 0 nodes. Trying simpler fallback for {provider}...")
            #         fallback_docs = await self._fallback_extract(text)
            #         if fallback_docs and fallback_docs[0].nodes:
            #             return fallback_docs
            if not docs or not docs[0].nodes:
                print(f"[KnowledgeGraph] Primary extraction returned 0 nodes.")
                print(f"[KnowledgeGraph] Text: {text}")
            
            return docs
        except Exception as e:
            # if fallback_on_empty:
            #     print(f"[KnowledgeGraph] Primary extraction failed: {e}. Trying fallback...")
            #     return await self._fallback_extract(text)
            print(f"[KnowledgeGraph] Extraction failed: {e}")
            print(f"[KnowledgeGraph] Text: {text}")
            raise e

    async def _fallback_extract(self, text: str) -> list:
        """Simpler extraction for models that struggle with LLMGraphTransformer."""
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import JsonOutputParser
        from langchain_neo4j.graphs.graph_document import GraphDocument, Node, Relationship
        from langchain_core.documents import Document

        prompt = ChatPromptTemplate.from_template("""
        Extract a knowledge graph from the following text based on this schema:
        Nodes: {nodes}
        Relationships: {relationships}
        
        Format the output as a JSON object with "nodes" and "relationships" keys.
        Each node must have "id" and "type".
        Each relationship must have "source", "target", and "type".
        
        Text: {text}
        
        Output JSON:
        """)
        
        chain = prompt | self._llm | JsonOutputParser()
        
        try:
            result = await chain.ainvoke({
                "nodes": ", ".join(self.schema.allowed_nodes),
                "relationships": ", ".join([f"({s})-[:{r}]->({t})" for s, r, t in self.schema.allowed_relationships[:10]]), # Limit to first 10 for brevity
                "text": text[:2000] # Limit text
            })
            
            nodes = []
            node_map = {}
            for n in result.get("nodes", []):
                # Map 'label' to 'type' if model used it
                ntype = n.get("type") or n.get("label", "Skill")
                node = Node(id=str(n.get("id")), type=ntype, properties=n)
                nodes.append(node)
                node_map[str(n.get("id"))] = node
                
            relationships = []
            for r in result.get("relationships", []):
                source_id = str(r.get("source"))
                target_id = str(r.get("target"))
                if source_id in node_map and target_id in node_map:
                    rel = Relationship(
                        source=node_map[source_id],
                        target=node_map[target_id],
                        type=r.get("type", "RELATED_TO"),
                        properties=r
                    )
                    relationships.append(rel)
                    
            if not nodes:
                return []
                
            return [GraphDocument(nodes=nodes, relationships=relationships, source=Document(page_content=text))]
        except Exception as e:
            print(f"[KnowledgeGraph] Fallback extraction failed: {e}")
            return []
    
    def extract_many(self, texts: list[str]) -> list:
        """
        Extract from multiple texts.
        
        Args:
            texts: List of texts to process.
            
        Returns:
            List of GraphDocument objects from all texts.
        """
        return self._transformer.process_texts(texts)
    
    async def aextract_many(self, texts: list[str]) -> list:
        """
        Extract from multiple texts asynchronously.
        
        Args:
            texts: List of texts to process.
            
        Returns:
            List of GraphDocument objects.
        """
        return await self._transformer.aprocess_texts(texts)
    
    # ==================== Database Operations ====================
    
    def add_documents(
        self,
        documents: list,
        include_source: bool = False,
        base_entity_label: bool = True,
        normalize: bool = True,
    ) -> None:
        """
        Add graph documents to the database.
        
        Args:
            documents: List of GraphDocument objects.
            include_source: Whether to include source document nodes.
            base_entity_label: Whether to add __Entity__ label.
        """
        normalized = self._normalize_documents(documents) if normalize else documents
        self._db.add_graph_documents(
            normalized,
            include_source=include_source,
            base_entity_label=base_entity_label,
        )
    
    def extract_and_add(
        self,
        text: str,
        include_source: bool = False,
        base_entity_label: bool = True,
    ) -> list:
        """
        Extract from text and add to database in one step.
        
        Args:
            text: Text to process.
            include_source: Whether to include source document.
            base_entity_label: Whether to add __Entity__ label.
            
        Returns:
            List of extracted GraphDocument objects.
        """
        documents = self.extract(text)
        self.add_documents(documents, include_source, base_entity_label)
        return documents
    
    async def aextract_and_add(
        self,
        text: str,
        include_source: bool = False,
        base_entity_label: bool = True,
    ) -> list:
        """
        Extract and add asynchronously.
        
        Args:
            text: Text to process.
            include_source: Whether to include source document.
            base_entity_label: Whether to add __Entity__ label.
            
        Returns:
            List of extracted GraphDocument objects.
        """
        documents = await self.aextract(text)
        self.add_documents(documents, include_source, base_entity_label)
        return documents

    def _normalize_documents(self, documents: list) -> list:
        """Ensure extracted nodes have required properties for UI and match schema."""
        allowed = set(self._transformer.schema.allowed_nodes)
        
        # Create a map for case-insensitive matching and synonyms
        type_map = {a.lower(): a for a in allowed}
        
        # Add common synonyms produced by LLMs
        synonyms = {
            "technology": "Tool",
            "library": "Tool",
            "framework": "Tool",
            "language": "Skill",
            "programming language": "Skill",
            "software": "Tool",
            "app": "Project",
            "application": "Project",
            "user": "Person",
            "assistant": "Person",
            "developer": "Person",
            "learner": "Person",
        }
        for k, v in synonyms.items():
            if v in allowed:
                type_map[k] = v

        normalized = []
        for doc in documents:
            nodes = []
            for node in doc.nodes:
                # Type normalization
                current_type = str(node.type)
                type_lower = current_type.lower()
                
                if type_lower in type_map:
                    node.type = type_map[type_lower]
                elif current_type.title() in allowed:
                    node.type = current_type.title()
                
                # Strict mode check
                if self._transformer.schema.strict_mode and node.type not in allowed:
                    continue
                
                # Property normalization
                if not node.properties.get("name"):
                    # Use ID if name is missing, clean up underscores/dashes
                    node.id = str(node.id)
                    node.properties["name"] = node.id.replace("_", " ").replace("-", " ").title()
                
                nodes.append(node)
            
            # Re-check relationships to ensure they point to existing nodes
            maintained_node_ids = {str(n.id) for n in nodes}
            relationships = []
            for rel in doc.relationships:
                if str(rel.source.id) in maintained_node_ids and str(rel.target.id) in maintained_node_ids:
                    # Also normalize source/target objects to have corrected types if needed
                    # Find maintained nodes to sync types
                    source_node = next((n for n in nodes if str(n.id) == str(rel.source.id)), None)
                    target_node = next((n for n in nodes if str(n.id) == str(rel.target.id)), None)
                    if source_node: rel.source.type = source_node.type
                    if target_node: rel.target.type = target_node.type
                    relationships.append(rel)
            
            doc.nodes = nodes
            doc.relationships = relationships
            normalized.append(doc)
        return normalized

    def normalize_documents(self, documents: list) -> list:
        """Public wrapper for document normalization."""
        return self._normalize_documents(documents)
    
    # ==================== Graph Management ====================
    
    def clean(self) -> None:
        """Delete all nodes and relationships from the graph."""
        self._db.clean_graph()
    
    def clean_by_label(self, label: str) -> int:
        """
        Delete all nodes with a specific label.
        
        Args:
            label: Node label to delete.
            
        Returns:
            Number of nodes deleted.
        """
        return self._db.clean_by_label(label)
    
    def merge_duplicates(self, label: str, match_property: str = "id") -> int:
        """
        Merge duplicate nodes based on a property.
        
        Args:
            label: Node label to merge.
            match_property: Property to match on.
            
        Returns:
            Number of nodes merged/deleted.
        """
        if label not in {"Skill", "Concept", "Topic"}:
            raise ValueError("Merge is only allowed for Skill, Concept, or Topic nodes")
        try:
            return self._db.merge_nodes(label, match_property)
        except Exception:
            # Fall back to simple merge if APOC not available
            return self._db.merge_nodes_simple(label, match_property)
    
    def merge_all_duplicates(self) -> dict:
        """
        Merge duplicates for all node labels in the schema.
        
        Returns:
            Dictionary mapping label to number of nodes merged.
        """
        results = {}
        for label in self.schema.allowed_nodes:
            try:
                count = self.merge_duplicates(label)
                if count > 0:
                    results[label] = count
            except Exception:
                pass
        return results
    
    # ==================== Query Operations ====================
    
    def query(self, cypher: str, params: Optional[dict] = None) -> list[dict]:
        """
        Execute a custom Cypher query.
        
        Args:
            cypher: Cypher query string.
            params: Query parameters.
            
        Returns:
            List of result dictionaries.
        """
        return self._db.query(cypher, params)
    
    def get_stats(self) -> dict:
        """
        Get graph statistics.
        
        Returns:
            Dictionary with node and relationship counts.
        """
        return self._db.get_graph_stats()
    
    def get_nodes(self, label: Optional[str] = None, limit: int = 100) -> list[dict]:
        """
        Get nodes from the graph.
        
        Args:
            label: Optional label to filter by.
            limit: Maximum number of nodes.
            
        Returns:
            List of node dictionaries.
        """
        return self._db.get_all_nodes(label, limit)
    
    def get_relationships(self, limit: int = 100) -> list[dict]:
        """
        Get relationships from the graph.
        
        Args:
            limit: Maximum number of relationships.
            
        Returns:
            List of relationship dictionaries.
        """
        return self._db.get_all_relationships(limit)
    
    def visualize(self):
        """
        Get visualization data for the graph.
        
        Returns:
            neo4j_viz VisualizationGraph object.
        """
        return self._db.visualize_graph()
    
    # ==================== Lifecycle ====================
    
    def close(self) -> None:
        """Close all connections."""
        self._db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
