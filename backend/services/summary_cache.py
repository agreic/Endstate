"""
Project Summary Cache Service
Handles storing and retrieving project summaries.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class SummaryCache:
    """Manages project summaries stored in local cache."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the summary cache."""
        self.cache_dir = cache_dir or (Path.home() / ".endstate" / "summaries")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_path(self, project_id: str) -> Path:
        """Get the file path for a project summary."""
        return self.cache_dir / f"{project_id}.json"
    
    def save(self, project_id: str, summary: Dict[str, Any]) -> bool:
        """
        Save a project summary.
        
        Args:
            project_id: Unique project identifier
            summary: Summary data to save
            
        Returns:
            True if successful
        """
        try:
            summary["session_id"] = project_id
            summary["created_at"] = datetime.utcnow().isoformat()
            summary["updated_at"] = datetime.utcnow().isoformat()
            
            file_path = self.get_path(project_id)
            with open(file_path, 'w') as f:
                json.dump(summary, f, indent=2)
            return True
        except Exception:
            return False
    
    def load(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a project summary.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Summary data or None if not found
        """
        file_path = self.get_path(project_id)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def delete(self, project_id: str) -> bool:
        """
        Delete a project summary.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if deleted, False if not found
        """
        file_path = self.get_path(project_id)
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            return True
        except Exception:
            return False
    
    def list_all(self) -> list[Dict[str, Any]]:
        """
        List all project summaries.
        
        Returns:
            List of project metadata (without full content)
        """
        projects = []
        for file_path in self.cache_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    projects.append({
                        "id": data.get("session_id"),
                        "name": data.get("agreed_project", {}).get("name", "Untitled"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "interests": data.get("user_profile", {}).get("interests", []),
                    })
            except Exception:
                continue
        
        return sorted(projects, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def exists(self, project_id: str) -> bool:
        """Check if a project summary exists."""
        return self.get_path(project_id).exists()

    def get_chat_path(self, project_id: str) -> Path:
        """Get the file path for a project chat history."""
        return self.cache_dir / f"{project_id}_chat.json"

    def save_chat_history(self, project_id: str, messages: list[dict]) -> bool:
        """
        Save chat history as JSON.

        Args:
            project_id: Project identifier (same as session_id)
            messages: List of messages with role, content, timestamp

        Returns:
            True if successful
        """
        try:
            file_path = self.get_chat_path(project_id)
            with open(file_path, 'w') as f:
                json.dump(messages, f, indent=2)
            return True
        except Exception:
            return False

    def load_chat_history(self, project_id: str) -> Optional[list[dict]]:
        """
        Load chat history.

        Args:
            project_id: Project identifier

        Returns:
            List of messages or None if not found
        """
        file_path = self.get_chat_path(project_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def delete_chat_history(self, project_id: str) -> bool:
        """
        Delete chat history file.

        Args:
            project_id: Project identifier

        Returns:
            True if deleted, False if not found or error
        """
        file_path = self.get_chat_path(project_id)
        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            return True
        except Exception:
            return False


# Global cache instance
summary_cache = SummaryCache()
