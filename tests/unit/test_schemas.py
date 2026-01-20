"""
Unit tests for graph schema classes.
"""

from backend.schemas.base import GraphSchema
from backend.schemas.skill_graph import SkillGraphSchema, MinimalSkillSchema, ContentExtractionSchema


class TestGraphSchema:
    """Tests for base GraphSchema class."""

    def test_schema_creation(self):
        """Test creating a basic schema."""
        schema = GraphSchema(
            name="Test Schema",
            description="A test schema",
            allowed_nodes=["NodeA", "NodeB"],
            allowed_relationships=[
                ("NodeA", "RELATES_TO", "NodeB"),
            ],
        )

        assert schema.name == "Test Schema"
        assert schema.description == "A test schema"
        assert schema.allowed_nodes == ["NodeA", "NodeB"]
        assert ("NodeA", "RELATES_TO", "NodeB") in schema.allowed_relationships
        assert schema.node_properties is False
        assert schema.relationship_properties is False
        assert schema.strict_mode is True

    def test_schema_with_properties(self):
        """Test schema with property definitions."""
        schema = GraphSchema(
            name="Test Schema",
            description="A test schema",
            allowed_nodes=["NodeA"],
            allowed_relationships=[],
            node_properties=["name", "description"],
            relationship_properties=["strength"],
        )

        assert schema.node_properties == ["name", "description"]
        assert schema.relationship_properties == ["strength"]

    def test_schema_with_auto_properties(self):
        """Test schema with auto property detection."""
        schema = GraphSchema(
            name="Test Schema",
            description="A test schema",
            allowed_nodes=["NodeA"],
            allowed_relationships=[],
            node_properties=True,
            relationship_properties=True,
        )

        assert schema.node_properties is True
        assert schema.relationship_properties is True

    def test_schema_strict_mode(self):
        """Test schema strict mode."""
        schema = GraphSchema(
            name="Test Schema",
            description="A test schema",
            allowed_nodes=["NodeA"],
            allowed_relationships=[],
            strict_mode=False,
        )

        assert schema.strict_mode is False

    def test_to_transformer_kwargs_defaults(self):
        """Test transformer kwargs with default properties."""
        schema = GraphSchema(
            name="Test Schema",
            description="A test schema",
            allowed_nodes=["NodeA"],
            allowed_relationships=[("NodeA", "LINKED_TO", "NodeA")],
        )

        kwargs = schema.to_transformer_kwargs()

        assert kwargs["allowed_nodes"] == ["NodeA"]
        assert kwargs["allowed_relationships"] == [("NodeA", "LINKED_TO", "NodeA")]
        assert kwargs["strict_mode"] is True
        assert "node_properties" not in kwargs
        assert "relationship_properties" not in kwargs

    def test_to_transformer_kwargs_with_properties(self):
        """Test transformer kwargs with explicit properties."""
        schema = GraphSchema(
            name="Test Schema",
            description="A test schema",
            allowed_nodes=["NodeA"],
            allowed_relationships=[],
            node_properties=["name"],
            relationship_properties=["weight"],
        )

        kwargs = schema.to_transformer_kwargs()

        assert kwargs["node_properties"] == ["name"]
        assert kwargs["relationship_properties"] == ["weight"]

    def test_to_transformer_kwargs_with_auto_properties(self):
        """Test transformer kwargs with auto properties."""
        schema = GraphSchema(
            name="Test Schema",
            description="A test schema",
            allowed_nodes=["NodeA"],
            allowed_relationships=[],
            node_properties=True,
            relationship_properties=True,
        )

        kwargs = schema.to_transformer_kwargs()

        assert kwargs["node_properties"] is True
        assert kwargs["relationship_properties"] is True


class TestSkillGraphSchema:
    """Tests for default SkillGraphSchema."""

    def test_schema_exists(self):
        """Test that SkillGraphSchema is properly defined."""
        assert SkillGraphSchema.name == "Skill Dependency Graph"
        assert "Skill" in SkillGraphSchema.allowed_nodes
        assert "Concept" in SkillGraphSchema.allowed_nodes
        assert "Topic" in SkillGraphSchema.allowed_nodes

    def test_skill_dependencies(self):
        """Test skill dependency relationships exist."""
        rel_types = [(s, r, t) for s, r, t in SkillGraphSchema.allowed_relationships]

        assert ("Skill", "REQUIRES", "Skill") in rel_types
        assert ("Skill", "RELATED_TO", "Skill") in rel_types

    def test_concept_relationships(self):
        """Test concept relationship definitions."""
        rel_types = [(s, r, t) for s, r, t in SkillGraphSchema.allowed_relationships]

        assert ("Concept", "CONTAINS", "Skill") in rel_types
        assert ("Concept", "REQUIRES", "Concept") in rel_types

    def test_node_properties(self):
        """Test that node properties are defined."""
        props = SkillGraphSchema.node_properties
        assert isinstance(props, list)
        assert "name" in props
        assert "description" in props
        assert "difficulty" in props

    def test_relationship_properties(self):
        """Test that relationship properties are defined."""
        props = SkillGraphSchema.relationship_properties
        assert isinstance(props, list)
        assert "strength" in props
        assert "reason" in props

    def test_strict_mode(self):
        """Test that strict mode is enabled."""
        assert SkillGraphSchema.strict_mode is True


class TestMinimalSkillSchema:
    """Tests for MinimalSkillSchema."""

    def test_minimal_nodes(self):
        """Test that minimal schema has fewer node types."""
        assert len(MinimalSkillSchema.allowed_nodes) == 3
        assert "Skill" in MinimalSkillSchema.allowed_nodes
        assert "Concept" in MinimalSkillSchema.allowed_nodes
        assert "Project" in MinimalSkillSchema.allowed_nodes

    def test_minimal_relationships(self):
        """Test that minimal schema has fewer relationships."""
        assert len(MinimalSkillSchema.allowed_relationships) == 3

    def test_strict_mode(self):
        """Test strict mode on minimal schema."""
        assert MinimalSkillSchema.strict_mode is True


class TestContentExtractionSchema:
    """Tests for ContentExtractionSchema."""

    def test_content_nodes(self):
        """Test content extraction schema nodes."""
        assert "Skill" in ContentExtractionSchema.allowed_nodes
        assert "Concept" in ContentExtractionSchema.allowed_nodes
        assert "Topic" in ContentExtractionSchema.allowed_nodes
        assert "Tool" in ContentExtractionSchema.allowed_nodes
        assert "Person" in ContentExtractionSchema.allowed_nodes

    def test_auto_properties(self):
        """Test that auto properties are enabled."""
        assert ContentExtractionSchema.node_properties is True
        assert ContentExtractionSchema.relationship_properties is True

    def test_person_relationships(self):
        """Test person-related relationships."""
        rel_types = [(s, r, t) for s, r, t in ContentExtractionSchema.allowed_relationships]

        assert ("Person", "EXPERT_IN", "Skill") in rel_types
        assert ("Person", "CREATED", "Tool") in rel_types
