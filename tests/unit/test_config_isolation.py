import pytest
import asyncio
from backend.config import (
    X_GEMINI_API_KEY, X_OPENROUTER_API_KEY, 
    X_NEO4J_URI, X_NEO4J_USERNAME, X_NEO4J_PASSWORD,
    config
)
from backend.main import extract_config_headers
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_request_scoped_isolation():
    """Verify that headers from one request don't leak into another."""
    
    # Original values from config (backend defaults)
    orig_uri = config.neo4j.uri
    
    async def mock_call_next(request):
        # inside the "request", check if context is set
        return {
            "uri": X_NEO4J_URI.get(),
            "user": X_NEO4J_USERNAME.get()
        }

    # Request A with overrides
    req_a = MagicMock()
    req_a.headers = {
        "X-Neo4j-URI": "bolt://request-a:7687",
        "X-Neo4j-User": "user-a"
    }
    
    # Request B with different overrides
    req_b = MagicMock()
    req_b.headers = {
        "X-Neo4j-URI": "bolt://request-b:7687",
        "X-Neo4j-User": "user-b"
    }

    # Request C with NO overrides
    req_c = MagicMock()
    req_c.headers = {}

    # Run them "concurrently" (simulated by sequence here as they restore tokens)
    res_a = await extract_config_headers(req_a, mock_call_next)
    res_b = await extract_config_headers(req_b, mock_call_next)
    res_c = await extract_config_headers(req_c, mock_call_next)

    # Assertions
    assert res_a["uri"] == "bolt://request-a:7687"
    assert res_a["user"] == "user-a"
    
    assert res_b["uri"] == "bolt://request-b:7687"
    assert res_b["user"] == "user-b"
    
    # Request C should fall back to backend defaults
    assert res_c["uri"] == "" # Default in ContextVar is ""
    assert config.neo4j.uri == orig_uri # The global config object still uses env if ContextVar is empty

@pytest.mark.asyncio
async def test_empty_header_discarded():
    """Verify that whitespace/empty headers are ignored."""
    
    async def mock_call_next(request):
        return X_NEO4J_PASSWORD.get()

    # Request with whitespace password
    req = MagicMock()
    req.headers = {"X-Neo4j-Password": "   "}
    
    res = await extract_config_headers(req, mock_call_next)
    
    # Should be empty string (the ContextVar default), NOT the whitespace
    assert res == ""
    # And global config should still return its default
    assert config.neo4j.password != "   "
