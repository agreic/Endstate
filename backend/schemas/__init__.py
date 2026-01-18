"""
Graph schemas for Endstate knowledge graphs.
Defines allowed node types, relationship types, and their properties.
"""
from .skill_graph import SkillGraphSchema
from .base import GraphSchema

__all__ = ["SkillGraphSchema", "GraphSchema"]
