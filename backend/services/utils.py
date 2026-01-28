"""
Shared utilities for backend services.
"""
import json
import re
from typing import Optional, Any

def extract_json(content: str) -> Optional[dict]:
    """
    Robustly extract JSON from a string that may contain markdown fences or extra text.
    
    Tries multiple strategies:
    1. Look for ```json ... ``` blocks
    2. Look for any ``` ... ``` blocks
    3. Look for the first '{' and last '}'
    """
    if not content:
        return None
        
    # Strategy 1: Markdown JSON block
    match = re.search(r"```json\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    # Strategy 2: Any markdown code block
    match = re.search(r"```\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    # Strategy 3: Naked JSON object
    match = re.search(r"(\{.*\})", content, flags=re.DOTALL)
    if match:
        obj_text = match.group(1)
        try:
            return json.loads(obj_text)
        except json.JSONDecodeError:
            # Try a simple repair: remove trailing commas before closing braces
            # This is common in LLM outputs
            repaired = re.sub(r",\s*([\]}])", r"\1", obj_text)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
                
    return None

def clean_markdown(content: str) -> str:
    """Remove markdown code fences from a string."""
    content = content.replace("```json", "").replace("```", "").strip()
    return content
