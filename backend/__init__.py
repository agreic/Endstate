"""
Endstate Backend - Knowledge-graph powered learning platform.

Quick Start:
    ```python
    from backend import KnowledgeGraphService
    
    # Initialize with Gemini (default)
    service = KnowledgeGraphService()
    
    # Or use local Ollama
    service = KnowledgeGraphService(llm_provider="ollama")
    
    # Extract and add to graph
    await service.aextract_and_add('''
        Python is a programming language that requires understanding of variables.
        Variables are fundamental to learning functions.
        Functions are essential for object-oriented programming.
    ''')
    
    # Get stats
    print(service.get_stats())
    
    # Clean graph
    service.clean()
    ```

For more details, see the individual modules:
    - backend.config: Configuration management
    - backend.db: Neo4j database client
    - backend.llm: LLM providers and graph transformation
    - backend.schemas: Graph schema definitions
    - backend.services: High-level service layer
"""
from .config import config, Config, Neo4jConfig, LLMConfig, OllamaConfig, GeminiConfig
from .db import Neo4jClient
from .llm import get_llm, LLMProvider, GraphTransformer
from .schemas import GraphSchema, SkillGraphSchema
from .services import KnowledgeGraphService

__all__ = [
    # Config
    "config",
    "Config",
    "Neo4jConfig",
    "LLMConfig",
    "OllamaConfig",
    "GeminiConfig",
    # Database
    "Neo4jClient",
    # LLM
    "get_llm",
    "LLMProvider",
    "GraphTransformer",
    # Schemas
    "GraphSchema",
    "SkillGraphSchema",
    # Services
    "KnowledgeGraphService",
]

__version__ = "0.1.0"
