"""
Base schema classes for graph definitions.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GraphSchema:
    """
    Base class for defining graph schemas.
    
    Attributes:
        name: Human-readable name for the schema
        description: Description of what this schema represents
        allowed_nodes: List of allowed node types (labels)
        allowed_relationships: List of (source_type, relationship_type, target_type) tuples
        node_properties: List of property names to extract for nodes, or True for auto
        relationship_properties: List of property names for relationships, or True for auto
        strict_mode: Whether to enforce schema strictly (remove non-conforming data)
    """
    name: str
    description: str
    allowed_nodes: list[str]
    allowed_relationships: list[tuple[str, str, str]]
    node_properties: list[str] | bool = False
    relationship_properties: list[str] | bool = False
    strict_mode: bool = True
    
    def to_transformer_kwargs(self) -> dict:
        """Convert schema to LLMGraphTransformer keyword arguments."""
        kwargs = {
            "allowed_nodes": self.allowed_nodes,
            "allowed_relationships": self.allowed_relationships,
            "strict_mode": self.strict_mode,
        }
        if self.node_properties:
            kwargs["node_properties"] = self.node_properties
        if self.relationship_properties:
            kwargs["relationship_properties"] = self.relationship_properties
        return kwargs
