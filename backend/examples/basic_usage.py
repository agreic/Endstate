#!/usr/bin/env python3
"""
Example usage of Endstate backend.

This script demonstrates how to use the KnowledgeGraphService
to extract knowledge from text and populate a Neo4j database.

Usage:
    # Using Gemini (requires GOOGLE_API_KEY env var)
    python -m backend.examples.basic_usage
    
    # Using Ollama (requires local Ollama server)
    LLM_PROVIDER=ollama python -m backend.examples.basic_usage
"""
import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend import KnowledgeGraphService
from backend.schemas.skill_graph import SkillGraphSchema, MinimalSkillSchema


# Example educational content about Python
SAMPLE_TEXT = """
Python is a high-level programming language known for its readability and simplicity.
To learn Python, you first need to understand variables, which store data values.
After mastering variables, you can learn about data types like strings, integers, and lists.

Functions are reusable blocks of code that require understanding of variables and control flow.
Control flow includes concepts like if statements and loops, which depend on boolean logic.

Object-Oriented Programming (OOP) is an advanced concept that builds on functions and data types.
OOP includes concepts like classes, inheritance, and polymorphism.
Classes require understanding of functions and variables.

For web development with Python, you need to learn frameworks like Django or Flask.
Django requires understanding of OOP, databases, and HTTP protocols.
Flask is simpler and requires OOP and basic understanding of HTTP.

Machine Learning with Python requires NumPy for numerical computing and Pandas for data manipulation.
NumPy requires understanding of variables, data types, and arrays.
Pandas builds on NumPy and requires understanding of DataFrames.
Scikit-learn is a machine learning library that requires NumPy, Pandas, and understanding of algorithms.
"""


async def main():
    """Main example function."""
    print("=" * 60)
    print("Endstate Knowledge Graph Service - Example Usage")
    print("=" * 60)
    
    # Check which provider to use
    provider = os.getenv("LLM_PROVIDER", "gemini")
    print(f"\n📡 Using LLM provider: {provider}")
    
    # Initialize service
    print("\n🔧 Initializing KnowledgeGraphService...")
    try:
        service = KnowledgeGraphService(llm_provider=provider)
    except ValueError as e:
        print(f"❌ Failed to initialize: {e}")
        print("   Set GOOGLE_API_KEY for Gemini or start Ollama for local LLM")
        return
    
    # Test connections
    print("\n🔍 Testing connections...")
    status = service.test_connection()
    
    if status["database"]:
        print("   ✅ Database connected")
    else:
        print(f"   ❌ Database error: {status['database_error']}")
        print("   Make sure Neo4j is running: docker-compose up -d")
        return
    
    if status["llm"]:
        print("   ✅ LLM connected")
    else:
        print(f"   ❌ LLM error: {status['llm_error']}")
        return
    
    # Clean the graph first
    print("\n🧹 Cleaning existing graph...")
    service.clean()
    print("   Done!")
    
    # Extract and add to graph
    print("\n📊 Extracting knowledge from sample text...")
    print(f"   Using schema: {service.schema.name}")
    print(f"   Allowed nodes: {', '.join(service.schema.allowed_nodes[:5])}...")
    
    documents = await service.aextract_and_add(
        SAMPLE_TEXT,
        include_source=True,
        base_entity_label=True,
    )
    
    print(f"   Extracted {len(documents)} graph document(s)")
    
    # Show extracted data
    if documents:
        doc = documents[0]
        print(f"\n   📝 Nodes extracted: {len(doc.nodes)}")
        for node in doc.nodes[:5]:
            print(f"      - [{node.type}] {node.id}")
        if len(doc.nodes) > 5:
            print(f"      ... and {len(doc.nodes) - 5} more")
        
        print(f"\n   🔗 Relationships extracted: {len(doc.relationships)}")
        for rel in doc.relationships[:5]:
            print(f"      - {rel.source.id} --[{rel.type}]--> {rel.target.id}")
        if len(doc.relationships) > 5:
            print(f"      ... and {len(doc.relationships) - 5} more")
    
    # Get and display stats
    print("\n📈 Graph Statistics:")
    stats = service.get_stats()
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Total relationships: {stats['total_relationships']}")
    
    print("\n   Nodes by type:")
    for label, count in stats.get("nodes", {}).items():
        print(f"      {label}: {count}")
    
    print("\n   Relationships by type:")
    for rel_type, count in stats.get("relationships", {}).items():
        print(f"      {rel_type}: {count}")
    
    # Merge duplicates
    print("\n🔄 Merging duplicate nodes...")
    merged = service.merge_all_duplicates()
    if merged:
        print(f"   Merged: {merged}")
    else:
        print("   No duplicates found")
    
    # Example custom query
    print("\n🔎 Example query - Find all skills that require other skills:")
    results = service.query("""
        MATCH (s:Skill)-[:REQUIRES]->(prereq:Skill)
        RETURN s.id as skill, prereq.id as prerequisite
        LIMIT 10
    """)
    
    for row in results:
        print(f"   {row['skill']} requires {row['prerequisite']}")
    
    if not results:
        print("   (No REQUIRES relationships found with Skill nodes)")
    
    print("\n" + "=" * 60)
    print("✅ Example completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. View graph in Neo4j Browser: http://localhost:7474")
    print("  2. Try different schemas (MinimalSkillSchema, ContentExtractionSchema)")
    print("  3. Process your own educational content")
    
    # Cleanup
    service.close()


if __name__ == "__main__":
    asyncio.run(main())
