#!/usr/bin/env python3
"""Utility script for cleaning up Neo4j Docker volumes and containers."""

import argparse
import sys
import docker


def cleanup_neo4j_resources(force: bool = False) -> None:
    """Clean up all Neo4j containers and volumes."""
    client = docker.from_env()
    
    print("🧹 Cleaning up Neo4j Docker resources...")
    
    # Stop and remove Neo4j containers
    try:
        containers = client.containers.list(all=True)
        neo4j_containers = [c for c in containers if 'neo4j' in c.name.lower()]
        
        for container in neo4j_containers:
            try:
                print(f"  📦 Removing container: {container.name}")
                container.remove(force=True)
            except Exception as e:
                print(f"  ⚠️  Failed to remove container {container.name}: {e}")
    except Exception as e:
        print(f"  ❌ Failed to list containers: {e}")
    
    # Remove Neo4j volumes
    try:
        volumes = client.volumes.list()
        neo4j_volumes = [v for v in volumes if v.name and 'neo4j' in v.name.lower()]
        
        for volume in neo4j_volumes:
            try:
                print(f"  💾 Removing volume: {volume.name}")
                volume.remove(force=force)
            except Exception as e:
                print(f"  ⚠️  Failed to remove volume {volume.name}: {e}")
                
    except Exception as e:
        print(f"  ❌ Failed to list volumes: {e}")
    
    # Also remove test volumes
    try:
        volumes = client.volumes.list()
        test_volumes = [v for v in volumes if v.name and 'test' in v.name.lower()]
        
        for volume in test_volumes:
            try:
                print(f"  🧪 Removing test volume: {volume.name}")
                volume.remove(force=force)
            except Exception as e:
                print(f"  ⚠️  Failed to remove test volume {volume.name}: {e}")
                
    except Exception as e:
        print(f"  ❌ Failed to list test volumes: {e}")
    
    print("✅ Cleanup completed!")


def list_neo4j_resources() -> None:
    """List all Neo4j containers and volumes."""
    client = docker.from_env()
    
    print("📋 Neo4j Docker Resources:")
    
    # List containers
    try:
        containers = client.containers.list(all=True)
        neo4j_containers = [c for c in containers if 'neo4j' in c.name.lower()]
        
        if neo4j_containers:
            print("\n  📦 Containers:")
            for container in neo4j_containers:
                status = container.status.upper()
                print(f"    - {container.name} ({status})")
        else:
            print("\n  📦 Containers: None")
            
    except Exception as e:
        print(f"  ❌ Failed to list containers: {e}")
    
    # List volumes
    try:
        volumes = client.volumes.list()
        neo4j_volumes = [v for v in volumes if v.name and 'neo4j' in v.name.lower()]
        
        if neo4j_volumes:
            print("\n  💾 Volumes:")
            for volume in neo4j_volumes:
                print(f"    - {volume.name}")
        else:
            print("\n  💾 Volumes: None")
            
    except Exception as e:
        print(f"  ❌ Failed to list volumes: {e}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Neo4j Docker cleanup utility")
    parser.add_argument(
        "command", 
        choices=["list", "cleanup"], 
        help="Command to run"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force removal of volumes (use with caution)"
    )
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_neo4j_resources()
    elif args.command == "cleanup":
        cleanup_neo4j_resources(force=args.force)


if __name__ == "__main__":
    main()