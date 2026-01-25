"""
Graph transformer module for converting text to knowledge graphs.
"""
from typing import Optional

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_experimental.graph_transformers import LLMGraphTransformer

from ..schemas.base import GraphSchema
from ..schemas.skill_graph import SkillGraphSchema
from ..config import config
from .provider import get_llm
from langchain_neo4j.graphs.graph_document import GraphDocument, Node, Relationship


class GraphTransformer:
    """
    Transforms text documents into knowledge graph structures.
    
    Uses LLM to extract entities and relationships according to a schema.
    """
    
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        schema: Optional[GraphSchema] = None,
        ignore_tool_usage: bool = False,
    ):
        """
        Initialize GraphTransformer.
        
        Args:
            llm: LangChain chat model. If not provided, uses default from config.
            schema: Graph schema defining allowed nodes/relationships.
                   Defaults to SkillGraphSchema.
            ignore_tool_usage: If True, use prompt-based extraction instead of tools.
        """
        self._llm = llm
        self._schema = schema or SkillGraphSchema
        self._ignore_tool_usage = ignore_tool_usage
        self._transformer: Optional[LLMGraphTransformer] = None
    
    @property
    def llm(self) -> BaseChatModel:
        """Get or create LLM instance."""
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
    
    @property
    def schema(self) -> GraphSchema:
        """Get current schema."""
        return self._schema
    
    @schema.setter
    def schema(self, value: GraphSchema) -> None:
        """Set schema and reset transformer."""
        self._schema = value
        self._transformer = None  # Reset to rebuild with new schema
    
    @property
    def transformer(self) -> LLMGraphTransformer:
        """Get or create LLMGraphTransformer instance."""
        if self._transformer is None:
            self._transformer = LLMGraphTransformer(
                llm=self.llm,
                ignore_tool_usage=self._ignore_tool_usage,
                **self._schema.to_transformer_kwargs(),
            )
        return self._transformer
    
    def convert_to_graph_documents(
        self,
        documents: list[Document],
    ) -> list:
        """
        Convert documents to graph documents synchronously.
        
        Args:
            documents: List of LangChain Document objects to process.
            
        Returns:
            List of GraphDocument objects containing extracted nodes and relationships.
        """
        return self.transformer.convert_to_graph_documents(documents)
    
    async def aconvert_to_graph_documents(
        self,
        documents: list[Document],
    ) -> list:
        """
        Convert documents to graph documents asynchronously.
        
        Recommended for processing multiple documents as it allows parallel processing.
        
        Args:
            documents: List of LangChain Document objects to process.
            
        Returns:
            List of GraphDocument objects containing extracted nodes and relationships.
        """
        return await self.transformer.aconvert_to_graph_documents(documents)
    
    def process_text(self, text: str) -> list:
        """
        Process raw text and extract graph documents.
        
        Convenience method that wraps text in a Document.
        
        Args:
            text: Raw text to process.
            
        Returns:
            List of GraphDocument objects.
        """
        if config.llm.provider == "mock":
            return self._mock_documents(text)
        documents = [Document(page_content=text)]
        return self.convert_to_graph_documents(documents)
    
    async def aprocess_text(self, text: str) -> list:
        """
        Process raw text asynchronously.
        
        Args:
            text: Raw text to process.
            
        Returns:
            List of GraphDocument objects.
        """
        if config.llm.provider == "mock":
            return self._mock_documents(text)
        documents = [Document(page_content=text)]
        return await self.aconvert_to_graph_documents(documents)
    
    def process_texts(self, texts: list[str]) -> list:
        """
        Process multiple texts and extract graph documents.
        
        Args:
            texts: List of text strings to process.
            
        Returns:
            List of GraphDocument objects from all texts.
        """
        if config.llm.provider == "mock":
            results = []
            for text in texts:
                results.extend(self._mock_documents(text))
            return results
        documents = [Document(page_content=text) for text in texts]
        return self.convert_to_graph_documents(documents)
    
    async def aprocess_texts(self, texts: list[str]) -> list:
        """
        Process multiple texts asynchronously.
        
        Args:
            texts: List of text strings to process.
            
        Returns:
            List of GraphDocument objects from all texts.
        """
        if config.llm.provider == "mock":
            results = []
            for text in texts:
                results.extend(self._mock_documents(text))
            return results
        documents = [Document(page_content=text) for text in texts]
        return await self.aconvert_to_graph_documents(documents)

    def _mock_documents(self, text: str) -> list:
        tokens = [t.strip(".,:;!?") for t in text.split() if t.isalpha()]
        primary = tokens[0] if tokens else "Mock Skill"
        secondary = tokens[1] if len(tokens) > 1 else "Mock Concept"
        primary_name = primary.strip() or "Mock Skill"
        secondary_name = secondary.strip() or "Mock Concept"
        node_a = Node(id=primary_name, type="Skill", properties={"name": primary_name})
        node_b = Node(id=secondary_name, type="Concept", properties={"name": secondary_name})
        rel = Relationship(source=node_a, target=node_b, type="DEPENDS_ON", properties={})
        return [GraphDocument(nodes=[node_a, node_b], relationships=[rel], source=Document(page_content=text))]
    
    def reset(self) -> None:
        """Reset the transformer (e.g., after schema change)."""
        self._transformer = None
