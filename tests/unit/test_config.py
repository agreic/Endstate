"""
Unit tests for configuration module.
"""
import os
from unittest.mock import patch

from backend.config import (
    Neo4jConfig,
    OllamaConfig,
    GeminiConfig,
    LLMConfig,
    Config,
)


class TestNeo4jConfig:
    """Tests for Neo4jConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            config = Neo4jConfig()
            assert config.uri == "bolt://localhost:7687"
            assert config.username == "neo4j"
            assert config.password == "password123"
            assert config.database == "neo4j"

    def test_from_environment(self):
        """Test configuration from environment variables."""
        env = {
            "NEO4J_URI": "bolt://neo4j.example.com:7687",
            "NEO4J_USERNAME": "admin",
            "NEO4J_PASSWORD": "secret",
            "NEO4J_DATABASE": "testdb",
        }
        with patch.dict(os.environ, env, clear=True):
            config = Neo4jConfig()
            assert config.uri == "bolt://neo4j.example.com:7687"
            assert config.username == "admin"
            assert config.password == "secret"
            assert config.database == "testdb"

    def test_uri_property(self):
        """Test URI property."""
        config = Neo4jConfig(_uri="bolt://custom:7687")
        assert config.uri == "bolt://custom:7687"


class TestOllamaConfig:
    """Tests for OllamaConfig class."""

    def test_default_values(self):
        """Test default Ollama configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = OllamaConfig()
            assert config.base_url == "http://localhost:11434"
            assert config.model == "llama3.2"
            assert config.temperature == 0.0

    def test_from_environment(self):
        """Test Ollama configuration from environment variables."""
        env = {
            "OLLAMA_BASE_URL": "http://ollama.example.com:11434",
            "OLLAMA_MODEL": "mistral",
        }
        with patch.dict(os.environ, env, clear=True):
            config = OllamaConfig()
            assert config.base_url == "http://ollama.example.com:11434"
            assert config.model == "mistral"

    def test_custom_temperature(self):
        """Test custom temperature setting."""
        config = OllamaConfig(temperature=0.7)
        assert config.temperature == 0.7


class TestGeminiConfig:
    """Tests for GeminiConfig class."""

    def test_default_values(self):
        """Test default Gemini configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = GeminiConfig()
            assert config.api_key == ""
            assert config.model == "gemini-2.5-flash-lite"
            assert config.temperature == 0.0

    def test_from_environment(self):
        """Test Gemini configuration from environment variables."""
        env = {
            "GOOGLE_API_KEY": "test_api_key_123",
            "GEMINI_MODEL": "gemini-pro",
        }
        with patch.dict(os.environ, env, clear=True):
            config = GeminiConfig()
            assert config.api_key == "test_api_key_123"
            assert config.model == "gemini-pro"


class TestLLMConfig:
    """Tests for LLMConfig class."""

    def test_default_provider(self):
        """Test default LLM provider is ollama."""
        with patch.dict(os.environ, {}, clear=True):
            config = LLMConfig()
            assert config.provider == "ollama"

    def test_ollama_provider(self):
        """Test Ollama provider configuration."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=True):
            config = LLMConfig()
            assert config.provider == "ollama"
            assert isinstance(config.ollama, OllamaConfig)

    def test_gemini_provider(self):
        """Test Gemini provider configuration."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini"}, clear=True):
            config = LLMConfig()
            assert config.provider == "gemini"
            assert isinstance(config.gemini, GeminiConfig)

    def test_nested_configs(self):
        """Test that nested configs are properly initialized."""
        config = LLMConfig()
        assert isinstance(config.ollama, OllamaConfig)
        assert isinstance(config.gemini, GeminiConfig)


class TestConfig:
    """Tests for main Config class."""

    def test_default_config(self):
        """Test default configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert isinstance(config.neo4j, Neo4jConfig)
            assert isinstance(config.llm, LLMConfig)

    def test_from_env_classmethod(self):
        """Test from_env classmethod."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=True):
            config = Config.from_env()
            assert config.llm.provider == "ollama"

    def test_config_override(self):
        """Test configuration override with custom values."""
        neo4j_config = Neo4jConfig(_uri="bolt://override:7687")
        config = Config(neo4j=neo4j_config)
        assert config.neo4j.uri == "bolt://override:7687"
