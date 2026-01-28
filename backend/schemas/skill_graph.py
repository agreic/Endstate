"""
Skill Graph Schema for Endstate learning platform.
Defines the structure for skill dependency graphs.
"""
from .base import GraphSchema


# Default schema for Endstate skill graphs
SkillGraphSchema = GraphSchema(
    name="Skill Dependency Graph",
    description="""
    Knowledge graph schema for learning paths and skill dependencies.
    Used by Endstate to map prerequisite relationships between skills,
    track learning progress, and generate personalized learning paths.
    """,
    
    # Node types for the learning domain
    allowed_nodes=[
        "Skill",              # A learnable skill or concept (e.g., "Python Variables")
        "Concept",            # An abstract concept (e.g., "Object-Oriented Programming")
        "Topic",              # A broader topic area (e.g., "Web Development")
        "Project",            # A capstone or practice project
        "Resource",           # Learning resource (tutorial, documentation, video)
        "Assessment",         # Quiz, test, or evaluation
        "Milestone",          # Learning milestone or checkpoint
        "Tool",               # Software tool or technology (e.g., "VS Code", "Git")
        "Domain",             # Application domain (e.g., "Data Science", "Game Dev")
        "Person",             # Learner or instructor
        "RemediationConcept", # Dynamically inserted prerequisite for remediation
    ],
    
    # Relationship types with source->target constraints
    allowed_relationships=[
        # Skill dependencies
        ("Skill", "REQUIRES", "Skill"),           # Skill A requires Skill B as prerequisite
        ("Skill", "RELATED_TO", "Skill"),         # Skills that are related but not dependent
        ("Skill", "PART_OF", "Concept"),          # Skill is part of a broader concept
        ("Skill", "PART_OF", "Topic"),            # Skill belongs to a topic
        
        # Concept relationships
        ("Concept", "CONTAINS", "Skill"),         # Concept contains multiple skills
        ("Concept", "REQUIRES", "Concept"),       # Concept dependencies
        ("Concept", "PART_OF", "Topic"),          # Concept belongs to a topic
        
        # Topic relationships
        ("Topic", "CONTAINS", "Concept"),         # Topic contains concepts
        ("Topic", "RELATED_TO", "Topic"),         # Related topics
        ("Topic", "APPLIED_IN", "Domain"),        # Topic applied in domain
        
        # Project relationships
        ("Project", "REQUIRES", "Skill"),         # Project requires certain skills
        ("Project", "DEMONSTRATES", "Concept"),   # Project demonstrates concepts
        ("Project", "USES", "Tool"),              # Project uses tools
        ("Project", "PART_OF", "Domain"),         # Project in a domain
        
        # Resource relationships
        ("Resource", "TEACHES", "Skill"),         # Resource teaches a skill
        ("Resource", "COVERS", "Concept"),        # Resource covers a concept
        ("Resource", "EXPLAINS", "Topic"),        # Resource explains a topic
        
        # Assessment relationships
        ("Assessment", "EVALUATES", "Skill"),     # Assessment evaluates skill mastery
        ("Assessment", "COVERS", "Concept"),      # Assessment covers concepts
        
        # Tool relationships
        ("Tool", "USED_FOR", "Skill"),            # Tool used for practicing skill
        ("Tool", "SUPPORTS", "Domain"),           # Tool supports a domain
        
        # Milestone relationships
        ("Milestone", "REQUIRES", "Skill"),       # Milestone requires skills
        ("Milestone", "UNLOCKS", "Skill"),        # Completing milestone unlocks new skills
        ("Milestone", "PART_OF", "Project"),      # Milestone is part of project
        
        # Person relationships (for tracking)
        ("Person", "MASTERED", "Skill"),          # Person has mastered a skill
        ("Person", "LEARNING", "Skill"),          # Person is currently learning
        ("Person", "COMPLETED", "Project"),       # Person completed a project
        ("Person", "INTERESTED_IN", "Topic"),     # Person's interests
    ],
    
    # Node properties to extract
    node_properties=[
        "name",               # Display name
        "description",        # Detailed description
        "difficulty",         # Difficulty level (beginner, intermediate, advanced)
        "estimated_hours",    # Estimated time to learn/complete
        "importance",         # How important (core, recommended, optional)
        "url",                # Link to resource
        "status",             # Current status (not_started, in_progress, completed)
        "mastery_score",      # 0-100 mastery percentage
    ],
    
    # Relationship properties
    relationship_properties=[
        "strength",           # How strong the relationship is (0-1)
        "reason",             # Why this relationship exists
        "created_at",         # When relationship was created
    ],
    
    strict_mode=True,
)


# Alternative minimal schema for simpler use cases
MinimalSkillSchema = GraphSchema(
    name="Minimal Skill Graph",
    description="Simplified schema with just skills and their dependencies.",
    allowed_nodes=["Skill", "Concept", "Project"],
    allowed_relationships=[
        ("Skill", "REQUIRES", "Skill"),
        ("Skill", "PART_OF", "Concept"),
        ("Project", "REQUIRES", "Skill"),
    ],
    node_properties=["name", "description", "difficulty"],
    relationship_properties=False,
    strict_mode=True,
)


# Schema for extracting knowledge from educational content
ContentExtractionSchema = GraphSchema(
    name="Content Extraction",
    description="Schema for extracting skills and concepts from educational text.",
    allowed_nodes=["Skill", "Concept", "Topic", "Tool", "Person"],
    allowed_relationships=[
        ("Skill", "REQUIRES", "Skill"),
        ("Skill", "RELATED_TO", "Skill"),
        ("Skill", "PART_OF", "Concept"),
        ("Concept", "REQUIRES", "Concept"),
        ("Concept", "PART_OF", "Topic"),
        ("Tool", "USED_FOR", "Skill"),
        ("Person", "EXPERT_IN", "Skill"),
        ("Person", "CREATED", "Tool"),
    ],
    node_properties=True,  # Let LLM decide what properties to extract
    relationship_properties=True,
    strict_mode=True,
)
